# -*- Mode: python -*-
#
# Copyright (C) 2000-2002 The ViewCVS Group. All Rights Reserved.
#
# By using this file, you agree to the terms and conditions set forth in
# the LICENSE.html file which can be found at the top level of the ViewCVS
# distribution or at http://viewcvs.sourceforge.net/license-1.html.
#
# Contact information:
#   Greg Stein, PO Box 760, Palo Alto, CA, 94302
#   gstein@lyra.org, http://viewcvs.sourceforge.net/
#
# -----------------------------------------------------------------------
#
# config.py: configuration utilities
#
# -----------------------------------------------------------------------
#

import sys
import os
import string
import ConfigParser
import fnmatch


#########################################################################
#
# CONFIGURATION
#
# There are three forms of configuration:
#
#       1) edit the viewcvs.conf created by the viewcvs-install(er)
#       2) as (1), but delete all unchanged entries from viewcvs.conf
#       3) do not use viewcvs.conf and just edit the defaults in this file
#
# Most users will want to use (1), but there are slight speed advantages
# to the other two options. Note that viewcvs.conf values are a bit easier
# to work with since it is raw text, rather than python literal values.
#
#########################################################################

class Config:
  _sections = ('general', 'options', 'cvsdb', 'templates')
  _force_multi_value = ('cvs_roots', 'forbidden', 'disable_enscript_lang',
                        'svn_roots', 'languages', 'kv_files',
                        'root_parents')

  def __init__(self):
    for section in self._sections:
      setattr(self, section, _sub_config())

  def load_config(self, fname, vhost=None):
    if hasattr(sys, 'argv'):
      this_dir = os.path.dirname(sys.argv[0])
    else:
      this_dir = ''
    pathname = os.path.join(this_dir, fname)
    self.base = os.path.dirname(pathname)

    self.conf_path = os.path.isfile(pathname) and pathname or None

    parser = ConfigParser.ConfigParser()
    parser.read(pathname)

    for section in self._sections:
      if parser.has_section(section):
        self._process_section(parser, section, section)

    if vhost and parser.has_section('vhosts'):
      self._process_vhost(parser, vhost)

  def load_kv_files(self, language):
    kv = _sub_config()

    for fname in self.general.kv_files:
      if fname[0] == '[':
        idx = string.index(fname, ']')
        parts = string.split(fname[1:idx], '.')
        fname = string.strip(fname[idx+1:])
      else:
        parts = [ ]
      fname = string.replace(fname, '%lang%', language)

      parser = ConfigParser.ConfigParser()
      parser.read(os.path.join(self.base, fname))
      for section in parser.sections():
        for option in parser.options(section):
          full_name = parts + [section]
          ob = kv
          for name in full_name:
            try:
              ob = getattr(ob, name)
            except AttributeError:
              c = _sub_config()
              setattr(ob, name, c)
              ob = c
          setattr(ob, option, parser.get(section, option))

    return kv

  def _process_section(self, parser, section, subcfg_name):
    sc = getattr(self, subcfg_name)

    for opt in parser.options(section):
      value = parser.get(section, opt)
      if opt in self._force_multi_value:
        value = map(string.strip, filter(None, string.split(value, ',')))
      else:
        try:
          value = int(value)
        except ValueError:
          pass

      if opt == 'cvs_roots' or opt == 'svn_roots':
        value = _parse_roots(opt, value)

      setattr(sc, opt, value)

  def _process_vhost(self, parser, vhost):
    canon_vhost = self._find_canon_vhost(parser, vhost)
    if not canon_vhost:
      # none of the vhost sections matched
      return

    cv = canon_vhost + '-'
    lcv = len(cv)
    for section in parser.sections():
      if section[:lcv] == cv:
        self._process_section(parser, section, section[lcv:])

  def _find_canon_vhost(self, parser, vhost):
    vhost = string.lower(vhost)
    # Strip (ignore) port number:
    vhost = string.split(vhost, ':')[0]

    for canon_vhost in parser.options('vhosts'):
      value = parser.get('vhosts', canon_vhost)
      patterns = map(string.lower, map(string.strip,
                                       filter(None, string.split(value, ','))))
      for pat in patterns:
        if fnmatch.fnmatchcase(vhost, pat):
          return canon_vhost

    return None

  def set_defaults(self):
    "Set some default values in the configuration."

    self.general.cvs_roots = { }
    self.general.svn_roots = { }
    self.general.root_parents = []
    self.general.default_root = ''
    self.general.rcs_path = ''
    if sys.platform == "win32":
      self.general.cvsnt_exe_path = 'cvs'
    else:
      self.general.cvsnt_exe_path = None
    self.general.use_rcsparse = 0
    self.general.mime_types_file = ''
    self.general.address = '<a href="mailto:user@insert.your.domain.here">No admin address has been configured</a>'
    self.general.main_title = 'Repository'
    self.general.forbidden = ()
    self.general.kv_files = [ ]
    self.general.languages = ['en-us']

    self.templates.directory = 'templates/directory.ezt'
    self.templates.log = 'templates/log.ezt'
    self.templates.query = 'templates/query.ezt'
    self.templates.diff = 'templates/diff.ezt'
    self.templates.graph = 'templates/graph.ezt'
    self.templates.annotate = 'templates/annotate.ezt'
    self.templates.markup = 'templates/markup.ezt'
    self.templates.error = 'templates/error.ezt'
    self.templates.query_form = 'templates/query_form.ezt'
    self.templates.query_results = 'templates/query_results.ezt'

    self.cvsdb.enabled = 0
    self.cvsdb.host = ''
    self.cvsdb.database_name = ''
    self.cvsdb.user = ''
    self.cvsdb.passwd = ''
    self.cvsdb.readonly_user = ''
    self.cvsdb.readonly_passwd = '' 
    self.cvsdb.row_limit = 1000

    self.options.root_as_url_component = 0
    self.options.sort_by = 'file'
    self.options.hide_attic = 1
    self.options.log_sort = 'date'
    self.options.diff_format = 'h'
    self.options.hide_cvsroot = 1
    self.options.hr_breakable = 1
    self.options.hr_funout = 1
    self.options.hr_ignore_white = 1
    self.options.hr_ignore_keyword_subst = 1
    self.options.allow_annotate = 1
    self.options.allow_markup = 1
    self.options.allow_compress = 1
    self.options.checkout_magic = 1
    self.options.docroot = None
    self.options.show_subdir_lastmod = 0
    self.options.show_logs = 1
    self.options.show_log_in_markup = 1
    self.options.cross_copies = 0
    self.options.py2html_path = '.'
    self.options.short_log_len = 80
    self.options.use_enscript = 0
    self.options.enscript_path = ''
    self.options.use_php = 0
    self.options.php_path = 'php'
    self.options.disable_enscript_lang = ()
    self.options.allow_tar = 0
    self.options.use_cvsgraph = 0
    self.options.cvsgraph_path = ''
    self.options.cvsgraph_conf = os.path.join(r"<VIEWCVS_INSTALL_DIRECTORY>", "cvsgraph.conf")
    self.options.use_re_search = 0
    self.options.use_pagesize = 0
    self.options.use_localtime = 0
    self.options.http_expiration_time = 600
    self.options.generate_etags = 1

  def is_forbidden(self, module):
    if not module:
      return 0
    default = 0
    for pat in self.general.forbidden:
      if pat[0] == '!':
        default = 1
        if fnmatch.fnmatchcase(module, pat[1:]):
          return 0
      elif fnmatch.fnmatchcase(module, pat):
        return 1
    return default


def _parse_roots(config_name, config_value):
  roots = { }
  for root in config_value:
    pos = string.find(root, ':')
    if pos < 0:
      raise MalformedRoot(config_name, root)
    name, path = map(string.strip, (root[:pos], root[pos+1:]))
    roots[name] = path
  return roots


class MalformedRoot(Exception):
  def __init__(self, config_name, value_given):
    Exception.__init__(self, config_name, value_given)
    self.config_name = config_name
    self.value_given = value_given
  def __str__(self):
    return "malformed configuration: '%s' uses invalid syntax: %s" \
           % (self.config_name, self.value_given)


class _sub_config:
  pass

if not hasattr(sys, 'hexversion'):
  # Python 1.5 or 1.5.1. fix the syntax for ConfigParser options.
  import regex
  ConfigParser.option_cre = regex.compile('^\([-A-Za-z0-9._]+\)\(:\|['
                                          + string.whitespace
                                          + ']*=\)\(.*\)$')
