#!/usr/bin/env python

# This file is part of hdl-syntax-checker.
#
# hdl-syntax-checker is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# hdl-syntax-checker is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with hdl-syntax-checker.  If not, see <http://www.gnu.org/licenses/>.

import os, re, logging, sys
import threading

################
# Build config #
################
TARGET_DIR = ".build"
if __name__ == '__main__':
    assert not os.system('mkdir -p ' + TARGET_DIR)

#######################
# Logging definitions #
#######################
# _LOG_FORMAT = "%(asctime)s | %(levelname)s | %(lineno)-3s | %(name)s %(message)s"
_LOG_FORMAT = "%(asctime)s <<%(levelname)-8s @ %(name)s >> %(message)s"
_LOG_LEVEL = logging.INFO
_LOG_FILE = os.path.sep.join([TARGET_DIR, "build.log"])

#  logging.basicConfig(format=_LOG_FORMAT, level=_LOG_LEVEL, filename=_LOG_FILE)

# logging.basicConfig(format=_LOG_FORMAT, level=_LOG_LEVEL, stream=sys.stdout)
_logger = logging.getLogger(__name__)

# _COMPILE_ORDER_DB = os.path.sep.join([TARGET_DIR, 'order.db'])
# _COMPILE_ORDER = None

_MAKE_DEF_BLOCK_STR = r"\s*[:?\b\s]=\s*"
_MAKE_DEF_BLOCK = re.compile(_MAKE_DEF_BLOCK_STR)
_MAKE_VAR = re.compile(r"^.*" + _MAKE_DEF_BLOCK_STR + ".*$")

CTAGS_ARGS = '--tag-relative=no --totals=no --sort=foldcase --extra=+f --fields=+i-l+m+s+S --links=yes'
CTAGS_VIM_CFG_FILE = os.path.sep.join([TARGET_DIR, 'vim.tags'])

_MAKEFILE_CACHE = {}
_MAKEFILE_CACHE_FILENAME = os.path.sep.join([TARGET_DIR, "makefile.cache"])

def read_makefile_cache():
    if not os.path.exists(_MAKEFILE_CACHE_FILENAME):
        return
    fd = open(_MAKEFILE_CACHE_FILENAME, 'r')
    try:
        global _MAKEFILE_CACHE
        _MAKEFILE_CACHE = eval(fd.read())
    finally:
        fd.close()

def write_makefile_cache():
    fd = open(_MAKEFILE_CACHE_FILENAME, 'w')
    fd.write(repr(_MAKEFILE_CACHE))
    fd.flush()
    fd.close()

#############################
# vcom arguments definition #
#############################
WARNINGS_TO_SUPPRESS = {
    'single' : (
        # vcom Message # 1320:
        # The expression of each element association of an array aggregate can be
        # of the element type or the type of the aggregate itself.  When an array
        # aggregate is of an array type whose element subtype is composite, it is
        # possible for certain kinds of its element association expressions to be
        # interpreted as being potentially either of these two types.  This will
        # normally happen only if the ambiguous expression is itself an aggregate
        # (because the type of an aggregate must be determined solely from the
        # context in which the aggregate appears, excluding the aggregate itself
        # but using the fact that the type of the aggregate shall be a composite
        # type) or a function call that identifies two overloaded functions.
        # This ambiguity is resolved in favor of the element type to support
        # backwards compatibility with prior versions of VHDL, in which the
        # element type was the only type considered.
        # [DOC: IEEE Std 1076-2008 VHDL LRM - 9.3.3.3 Array aggregates]
        #
        # Type of expression "(OTHERS => '0')" is ambiguous; using element type STD_LOGIC_VECTOR, not aggregate type bit3vec_t.
        1320,   #

        # 1239,
        # vcom Message # 1239:
        # An individual association element whose formal designator is a slice
        # of the formal has a slice discrete range with a direction different
        # from the would-be direction of the formal itself.
        # It is an error (null slice in VHDL 1987) if the direction of the
        # discrete range of a slice name is not the same as that of the index
        # range of the array denoted by the prefix of the slice name.
        #
        # However, in the case where the formal is of an unconstrained array
        # type (and thus the direction would normally come from the direction of
        # the index subtype of this base array type), the compiler will use the
        # direction of the first formal slice name that appears in the individual
        # association elements in the association list (all slices of this formal
        # must therefore have the same direction); this is non-compliant
        # behavior.
        # [DOC: IEEE Std 1076-1993 VHDL LRM - 6.5 Slice names]
        ),
    'batch' : []
    }

VCOM_BUILD_OPTS = {
    'single' : [
        '-explicit',
        '-defercheck',
        '-novopt',
        '-nocheck',
        '-check_synthesis',
        '-lint',
        '-rangecheck',
        # '-permissive',
        '-lrmconfigvis',],
    'batch' : [
        '-explicit',
        '-defercheck',
        '-novopt',
        '-nocheck',
        '-permissive',
        '-lrmconfigvis',
        ]
    }

BATCH_BUILD_WARNINGS_TO_SUPPRESS = None

if WARNINGS_TO_SUPPRESS['single']:
    VCOM_BUILD_OPTS['single'].append('-suppress ' + ','.join([str(x) for x in WARNINGS_TO_SUPPRESS['single']]))

if WARNINGS_TO_SUPPRESS['batch']:
    VCOM_BUILD_OPTS['batch'].append('-suppress ' + ','.join([str(x) for x in WARNINGS_TO_SUPPRESS['batch']]))

def find_files_in_path(path, f, recursive=True):
    """
    Finds files that match f(_file_), where _file_ is the relative path to the item found.
    """
    if recursive:
        for dirpath, _, filenames in os.walk(path):
            for filename in filenames:
                relpath_to_filename = os.path.sep.join([dirpath, filename])
                if f(relpath_to_filename):
                    yield os.path.normpath(relpath_to_filename)
    else:
        for l in os.listdir(path):
            l = os.path.sep.join([path, l])
            if not os.path.isfile(l):
                continue
            if f(l):
                yield os.path.normpath(l)

def _is_vhd(p):
    return os.path.basename(p).lower().endswith('vhd')

def _is_makefile(f):
    return os.path.basename(f) == 'Makefile'

def shell(cmd, exit_status = 0):
    """
    Dummy wrapper for running shell commands, checking the return value and logging
    """

    sts = os.system(cmd)

    if sts == exit_status:
        _logger.debug(cmd)
    else:
        if sts == 512:
            _logger.debug("'%s' returned %d (expected %d)", cmd, sts, exit_status)
        else:
            _logger.warning("'%s' returned %d (expected %d)", cmd, sts, exit_status)
    return sts


RE_VCOM_COMPILER_EXITING = re.compile(r".*VHDL Compiler exiting.*")
RE_VCOM_ERROR = re.compile(r"^\*\* Error:.*")
RE_VCOM_WARNING = re.compile(r"^\*\* Warning:.*")
RE_MAKEFILE_COMMENT = re.compile(r"#.*$")
RE_PATH_SEPARATOR = re.compile(os.path.sep)
RE_MAKEFILE_VARIABLE = re.compile(r".*\$\([^\)]*\).*")
RE_ONE_OR_MORE_WHITESPACES = re.compile(r"\s+")
RE_CTAGS_IGNORE_LINE = re.compile(r"^\s*$|ctags-exuberant: Warning: Language \"vhdl\" already defined")

RE_VCOM_RECOMPILE_ERROR_ID = re.compile(r"\(vcom-13\)")
RE_VCOM_RECOMPILE_LIBRARY = re.compile(r"^.*Recompile\s*|\.\w+\s*because\s*.*$")
RE_VCOM_RECOMPILE_SOURCE = re.compile(r"^.*Recompile\s*\w+\.|\s*because\s*.*$")


_logger_vcom = logging.getLogger('vcom')
_VCOM_SUBS = (
    (re.compile(r"\s*\[\d+\]\s*"), ""),
    # (re.compile(r"\s*\[1\]\s*"), "[Unbound component]"),
    # (re.compile(r"\s*\[2\]\s*"), "[Process without wait]"),
    # (re.compile(r"\s*\[3\]\s*"), "[Null range]"),
    # (re.compile(r"\s*\[4\]\s*"), "[No space in time literal]"),
    # (re.compile(r"\s*\[5\]\s*"), "[Multiple drivers on unresolved signal]"),
    # (re.compile(r"\s*\[10\]\s*"), "[VHDL-1993 in VHDL-1987]"),
    )

# _CODE_IDENTIFIERS = (
#     re.compile(r"\"[^\"]*\"", re.I),
#     )

_OPEN_FILES = []

def vcom(library, fname, modelsimini=None, extra_flags = '', logger=None):
    if logger is None:
        global _logger_vcom
    else:
        _logger_vcom = logger
    cmd = 'vcom ' + extra_flags
    if modelsimini:
        cmd += ' -modelsimini ' + modelsimini
    cmd += ' -work ' + library + ' ' + fname

    if fname in _OPEN_FILES:
        _logger_vcom.warning("File %s is already open", fname)
        raise RuntimeError("File %s is already open", fname)

    _OPEN_FILES.append(fname)
    _logger_vcom.info(cmd)
    ret = os.popen(cmd).read()
    _OPEN_FILES.remove(fname)
    sts = 0
    ret = ret.split("\n")

    errors = []
    warnings = []
    log_line = []
    for l in ret:
        if RE_VCOM_COMPILER_EXITING.match(l):
            continue
        # if re.match(r"^\*\* Warning:\s*\[\d+\]", l):
        #     l = re.sub(r"\s*\[\d+\]\s*", "", l)
        for re_obj, re_text in _VCOM_SUBS:
            l = re_obj.sub(re_text, l)
        log_line += [l]
        if RE_VCOM_ERROR.match(l):
            errors.append("\n".join(log_line))
            sts = 1
            log_line = []
        elif RE_VCOM_WARNING.match(l):
            warnings.append("\n".join(log_line))
            sts = 1
            log_line = []

    if errors or warnings:
        _logger_vcom.info("Messages found while running vcom")
        _logger_vcom.info("'%s'", cmd)
    if errors:
        _logger_vcom.info("=== Errors ===")
        for error in errors:
            _logger_vcom.info(error)

    if warnings:
        _logger_vcom.info("=== Warnings ===")
        for warning in warnings:
            _logger_vcom.info(warning)

    return sts, errors, warnings


class Makefile(object):

    CACHE_DIR = TARGET_DIR

    def __init__(self, make_fname, *vars_to_resolve):
        self.fname = make_fname

        _fname = RE_PATH_SEPARATOR.sub("__", self.fname)
        self._vars_to_resolve = vars_to_resolve
        self._logger = logging.getLogger("Makefile('%s')" % self.fname)
        self._vars_dict = {}
        self.library = '<undefined>'
        self.sources = []

        self._cached_variables_fname = os.path.sep.join([self.CACHE_DIR, _fname])
        self._cached_variables = {}

    def __str__(self):
        return "Makefile(make_fname='%s', %s)" % (self.fname, self._vars_to_resolve)

    def _do_extract_variables(self):
        self._logger.info("Extracting Makefile variables from '%s'", self.fname)
        cmd = 'ROOT_DIR="." make -np -f %s  2>&1 | sed -e "s/#.*//g" ' % self.fname
        self._vars_dict = {}
        for line in os.popen(cmd).read().split("\n"):
            line_nc = RE_MAKEFILE_COMMENT.sub("", line)
            if _MAKE_VAR.match(line_nc):
                defs = _MAKE_DEF_BLOCK.split(line_nc)
                if len(defs) != 2:
                    self._logger.error("Error parsing line")
                    self._logger.error(" - Filename: %s", self.fname)
                    self._logger.error(" - Line: %s", line)
                var_name, var_value = defs
                var_resolved_value = var_value
                self._vars_dict[var_name] = var_value

                if var_name in self._vars_to_resolve or len(self._vars_to_resolve) == 0:
                    if r"$" in var_value and RE_MAKEFILE_VARIABLE.match(var_value):
                        for existing_var_name, existing_var_value in self._vars_dict.iteritems():
                            var_resolved_value = re.sub(r"\$\(" + existing_var_name + r"\)", existing_var_value, var_resolved_value)

                self._cached_variables[var_name] = var_resolved_value
        self._cached_variables['timestamp'] = os.path.getmtime(self.fname)
        #  global _MAKEFILE_CACHE
        _MAKEFILE_CACHE[self._cached_variables_fname] = self._cached_variables

    def extract_variables(self):
        if self._cached_variables_fname not in _MAKEFILE_CACHE.keys():
            #  self._logger.info("No cached variables")
            self._do_extract_variables()
        else:
            self._read_variables_from_file_cache()
            if os.path.getmtime(self.fname) > self._cached_variables['timestamp'] :
                self._logger.info("Cached makefile data is out of date")
                self._do_extract_variables()
            else:
                self._logger.debug("Cached makefile data is up to date")


        return self._cached_variables

    # def _write_variables_to_file_cache(self):
    #     file_cache = open(self._cached_variables_fname, 'w')
    #     file_cache.write(repr(self._cached_variables))
    #     file_cache.close()

    def _read_variables_from_file_cache(self):
        self._cached_variables = _MAKEFILE_CACHE[self._cached_variables_fname]

    def _invalidate_cache(self):
        self._cached_variables = {}

    def _invalidate_cache_deep(self):
        self._invalidate_cache()
        os.remove(self._cached_variables_fname)

    def get(self, var_name):
        return self.extract_variables()[var_name]

class Library(object):

    MODELSIM_INI_PATH = 'modelsim.ini'

    def __init__(self, **kwargs):
        makefile = kwargs.get('makefile', None)
        name = kwargs.get('name', None)
        if makefile and name:
            raise RuntimeError("Can't use both 'makefile' and 'name' keywords")

        if makefile:
            self.makefile = Makefile(makefile, 'LIB', 'SOURCE_FILES', 'VCOM_ARGS_G', 'VCOM_ARGS')
            self.name = self.makefile.extract_variables()['LIB']
        elif name:
            self.makefile = None
            self.name = name

        self.build_at = kwargs.get('build_at')
        self.tagfile = os.path.sep.join([self.build_at, self.name + '.tags'])

        self._extra_flags = []
        self._sources = []
        self._logger = logging.getLogger("Library('%s')" % self.name)

        self._logger.debug("Creating library with parms %s", kwargs)

        self._compiled = []
        self._failed = []

        self._create_library()

    def __str__(self):
        if self.makefile:
            return "Library(makefile='%s', name='%s', build_at='%s')" % (self.makefile, self.name, self.build_at)
        else:
            return "Library(name='%s', build_at='%s')" % (self.name, self.build_at)

    def add_source(self, fname):
        if fname not in self._sources:
            self._sources.append(fname)
        else:
            self._logger.warning("File '%s' has already been added", fname)

    def remove_source(self, f):
        for source in self._sources:
            if f(source):
                self._sources.remove(source)

    def get_sources(self):
        _sources = []
        if self.makefile:
            try:
                #  _sources += re.split(r"\s+", self.makefile.extract_variables()['SOURCE_FILES'])
                _sources += RE_ONE_OR_MORE_WHITESPACES.split(self.makefile.extract_variables()['SOURCE_FILES'])
            except KeyError:
                # self._logger.warning("Makefile of library '%s' has no SOURCE_FILES", self.name)
                pass
        _sources += self._sources
        return _sources

    def _create_library(self):
        lib_path = os.path.sep.join([self.build_at, self.name])
        if os.path.exists(os.path.sep.join([lib_path, '_info'])):
            self._logger.debug("Library '%s' already exists at '%s', returning", self.name, lib_path)
            return

        self._logger.debug("Creating library '%s' at '%s'", self.name, lib_path)
        if not os.path.exists(self.MODELSIM_INI_PATH):
            self._logger.debug("[%s] Creating lib without modelsim.ini at %s", self.name, self.build_at)
            shell('vlib ' + lib_path + "; " + 'vmap ' + ' '.join([self.name, lib_path]) + ' > /dev/null')
        else:
            shell('vlib ' + lib_path + "; " + 'vmap -modelsimini ' + ' '.join([self.MODELSIM_INI_PATH, self.name, lib_path]) + ' > /dev/null')

    def add_build_opts(self, *flags):
        if type(flags) is str:
            self._extra_flags.append(flags)
            return

        for flag in flags:
            if flag not in self._extra_flags:
                self._extra_flags.append(flag)

    def build_single(self, source, extra_flags=[]):
        sources = [os.path.abspath(x) for x in self.get_sources()]
        if os.path.abspath(source) not in sources:
            self._logger.error(str(os.path.abspath(source)))
            self._logger.error("\n- ".join(self.get_sources()))
            raise RuntimeError("File '%s' is not in library '%s'" % (source, self.name))

        self._logger.debug("Building single file '%s'", source)
        self._logger.debug("extra_flags=%s", extra_flags)
        lib_path = os.path.sep.join([self.build_at, self.name])

        ref_file = os.path.sep.join([lib_path, "." + os.path.basename(source)]) + ".ran_vcom"
        if os.path.exists(ref_file):
            if os.path.getmtime(ref_file) > os.path.getmtime(source):
                self._logger.debug("Source is up to date")
                return [], []

        _extra_flags = []

        if extra_flags is not None:
            for _ef in extra_flags:
                _extra_flags.append(_ef)
        for _ef in self._extra_flags:
            _extra_flags.append(_ef)

        sts, errors, warnings = vcom(lib_path, source, self.MODELSIM_INI_PATH, " ".join(_extra_flags), logger=self._logger)
        if sts == 0:
            if source not in self._compiled:
                self._compiled.append(source)
            if source in self._failed:
                self._failed.remove(source)
            touch(ref_file)
        else:
            # for error in errors:
            #     print error
            # for warning in warnings:
            #     print warning

            if source in self._compiled:
                self._compiled.remove(source)
            if source not in self._failed:
                self._failed.append(source)
        return errors, warnings

    def build_lib(self, **kwargs):
        verbose = kwargs.pop('verbose', False)
        if self.makefile:
            self._logger.info("Building library '%s'", self.makefile)
            self._build_from_makefile(verbose)
        else:
            self._logger.info("Building library '%s'", self.name)
        self._build_added_sources(verbose=verbose, **kwargs)

    def build_tags(self):
        ctags = ['ctags-exuberant']
        ctags += [CTAGS_ARGS]
        ctags += ['-f ' + self.tagfile]

        if os.path.exists(self.tagfile):
            ctags_mtime = os.path.getmtime(self.tagfile)
        else:
            ctags_mtime = 0

        rebuild = False

        sources = []

        for source in self.get_sources():
            if source == '':
                continue
            if not os.path.exists(source):
                # _logger.warning("Source file '%s' doesn't exists", source)
                continue

            sources.append(os.path.abspath(source))

            if os.path.getmtime(source) > ctags_mtime:
                rebuild = True

        if rebuild and sources:
            cmd = " ".join(ctags + sources) + ' 2>&1 &'
            self._logger.info(cmd)

            for _l in os.popen(cmd).read().split("\n"):
                if not RE_CTAGS_IGNORE_LINE.match(_l):
                    self._logger.info(_l)

    def _build_from_makefile(self, verbose):
        try:
            sources = RE_ONE_OR_MORE_WHITESPACES.split(self.makefile.extract_variables()['SOURCE_FILES'])
        except KeyError:
            self._logger.warning("Unable to get sources from makefile")
            return
        try:
            vcom_args = self.makefile.extract_variables()['VCOM_ARGS_G']
        except KeyError:
            vcom_args = ''
        try:
            vcom_args += self.makefile.extract_variables()['VCOM_ARGS']
        except KeyError:
            pass
        r = self._build_from_list(sources, extra_flags = [vcom_args], verbose=verbose)
        if len(self._compiled) == 0 and len(self._failed) == 0 and len(self.get_sources()) == 0:
            raise RuntimeError("Library %s could not build any files" % self.name)
        return r

    def _build_added_sources(self, **kwargs):
        return self._build_from_list(self._sources, **kwargs)

    def _build_from_list_alt(self, sources, extra_flags = None, verbose=False):
        self._logger.debug("Building from list with parameters:")
        self._logger.debug("sources=%s", sources)
        self._logger.debug("extra_flags=%s", extra_flags)
        lib_path = os.path.sep.join([self.build_at, self.name])

        vcom_sources = []

        for source in sources:
            ref_file = os.path.sep.join([lib_path, "." + os.path.basename(source)]) + ".ran_vcom"
            if not os.path.exists(source):
                # _logger.warning("Source file '%s' doesn't exists", source)
                continue
            if os.path.exists(ref_file):
                if os.path.getmtime(ref_file) > os.path.getmtime(source):
                    continue

            vcom_sources.append(source)

        _extra_flags = []

        if extra_flags is not None:
            for _ef in extra_flags:
                _extra_flags.append(_ef)
        for _ef in self._extra_flags:
            _extra_flags.append(_ef)


        if vcom_sources:
            sts, errors_, warnings_ = vcom(lib_path, " ".join(vcom_sources), self.MODELSIM_INI_PATH, " ".join(_extra_flags + ['-just p']), logger=self._logger)
            sts, errors, warnings = vcom(lib_path, " ".join(vcom_sources), self.MODELSIM_INI_PATH, " ".join(_extra_flags + ['-skip p']), logger=self._logger)
            errors += errors_
            warnings += warnings_

            sources_with_errors = []
            sources_with_warnings = []

            for error in errors:
                for n in re.findall(r"\b|\b".join(vcom_sources), error):
                    if n not in sources_with_warnings:
                        sources_with_errors.append(n)
                # if not verbose:
                #     print error

            for warning in warnings:
                for n in re.findall(r"\b|\b".join(vcom_sources), warning):
                    if n not in sources_with_warnings:
                        sources_with_warnings.append(n)
                # if not verbose:
                #     print warning

            for source in sources:
                if source in sources_with_errors + sources_with_warnings:
                    if source in self._compiled:
                        self._compiled.remove(source)
                    if source not in self._failed:
                        self._failed.append(source)
                else:
                    self._compiled.append(source)
                    if source in self._failed:
                        self._failed.remove(source)
                    ref_file = os.path.sep.join([lib_path, "." + os.path.basename(source)]) + ".ran_vcom"
                    touch(ref_file)


            # print warning

            # if sts == 0:
            #     if source not in self._compiled:
            #         self._compiled.append(source)
            #     if source in self._failed:
            #         self._failed.remove(source)
            #     touch(ref_file)
            # else:
            #     if not verbose:
            #         for error in errors:
            #             print error
            #         for warning in warnings:
            #             print warning

            #     if source in self._compiled:
            #         self._compiled.remove(source)
            #     if source not in self._failed:
            #         self._failed.append(source)

    def _source_built_ok(self, source):
        lib_path = os.path.sep.join([self.build_at, self.name])
        ref_file = os.path.sep.join([lib_path, "." + os.path.basename(source)]) + ".ran_vcom"
        touch(ref_file)
        if source not in self._compiled:
            self._compiled.append(source)
        if source in self._failed:
            self._failed.remove(source)

    def _source_built_with_errors(self, source):
        if source in self._compiled:
            self._compiled.remove(source)
        if source not in self._failed:
            self._failed.append(source)
    def _build_from_list(self, sources, extra_flags = None, verbose=False):
        self._logger.debug("Building from list with parameters:")
        self._logger.debug("sources=%s", sources)
        self._logger.debug("extra_flags=%s", extra_flags)
        lib_path = os.path.sep.join([self.build_at, self.name])
        for source in sources:
            ref_file = os.path.sep.join([lib_path, "." + os.path.basename(source)]) + ".ran_vcom"
            if source == '':
                continue
            if not os.path.exists(source):
                self._logger.warning("Source file '%s' doesn't exists", source)
                continue
            if os.path.exists(ref_file):
                if os.path.getmtime(ref_file) > os.path.getmtime(source):
                    continue

            _extra_flags = []

            if extra_flags is not None:
                for _ef in extra_flags:
                    _extra_flags.append(_ef)
            for _ef in self._extra_flags:
                _extra_flags.append(_ef)

            sts, errors, warnings = vcom(lib_path, source, self.MODELSIM_INI_PATH, " ".join(_extra_flags), logger=self._logger)

            if verbose:
                if errors or warnings:
                    self._source_built_with_errors(source)
                else:
                    self._source_built_ok(source)
                for warning in warnings:
                    print warning
                for error in errors:
                    print error
            else:
                if errors:
                    self._source_built_with_errors(source)
                else:
                    self._source_built_ok(source)

    def get_compiled(self):
        return self._compiled
    def get_failed(self):
        return self._failed

def build_until_stable(libraries, verbose):
    for _lib_name in ('base_lib', 'sync_lib', 'easics_packages', 'fifo_lib', 'check_lib', 'osvvm_lib',):
        if _lib_name in libraries.keys():
            libraries[_lib_name].build_lib(verbose=verbose)

    # Be the most permissive as possible we can have a working set of compiled binaries
    # to start checking from
    for lib in libraries.itervalues():
        lib.add_build_opts(*VCOM_BUILD_OPTS['batch'])
        # lib.add_build_opts('-explicit', '-defercheck', '-novopt', '-nocheck')
        # lib.add_build_opts('-permissive')
        # lib.add_build_opts('-lrmconfigvis')
    prev_failed_builds = []

    max_threads = 0
    while True:
        _threads = []

        thread_cnt = 0
        for lib in libraries.itervalues():
            this_thread = threading.Thread(target=lib.build_lib, kwargs={'verbose' : verbose})
            this_thread.start()
            _threads.append(this_thread)
            thread_cnt += 1
            if threading.active_count() > max_threads:
                max_threads = threading.active_count()
            if thread_cnt == Config.thread_limit:
                thread_cnt = 0
                for thread in _threads:
                    thread.join()
                _threads = []
        for thread in _threads:
            thread.join()

        failed_builds = []
        for lib in libraries.itervalues():
            _failed = lib.get_failed()
            if _failed:
                failed_builds.append((lib.name, _failed))
        if failed_builds == prev_failed_builds:
            _logger.info("Failed builds: %s", "\n".join([str(x) for x in failed_builds]))
            _logger.info("Number of failed builds is stable in %d", len(failed_builds))
            break
        _logger.debug("Number of failed builds is currently %d", len(failed_builds))
        _logger.debug("Failed builds: %s", "\n".join([str(x) for x in failed_builds]))
        prev_failed_builds = failed_builds

    if prev_failed_builds:
        try:
            from prettytable import PrettyTable
            failed_t = PrettyTable(["Library", "Files"])
            failed_t.align = 'l'
            for _lib, _f in prev_failed_builds:
                failed_t.add_row([_lib, "\n".join(_f)])
                failed_t.add_row(["", ""])
            failed_t.del_row(-1)
            if verbose:
                print failed_t
            else:
                _logger.info(str(failed_t))

        except ImportError:
            if verbose:
                print "Sources that failed to build:"
                for _lib, _f in prev_failed_builds:
                    print "[%s]  %s" % (_lib, " ".join(_f))
        finally:
            _logger.info("Maximum threads: %d", max_threads)
            if verbose:
                print "Maximum threads: %d" % max_threads

def _discover_recompiles(libraries, source, error):
    lib_name = source = None
    if RE_VCOM_RECOMPILE_ERROR_ID.match(error):
        lib_name = RE_VCOM_RECOMPILE_LIBRARY.sub("", error)
        source = RE_VCOM_RECOMPILE_SOURCE.sub("", error)
        #  lib_name = re.sub(r"^.*Recompile\s*|\.\w+\s*because\s*.*$", "", error)
        #  source = re.sub(r"^.*Recompile\s*\w+\.|\s*because\s*.*$", "", error)

    return lib_name, source

def rebuild(libraries, obj_hint):
    _logger.debug("rebuild with hint = %s", repr(obj_hint))
    found = False
    lib_name = None
    for lib_name, lib in libraries.iteritems():
        for source in lib.get_sources():
            if str(obj_hint) in source:
                found = True
                _logger.info("Found %s in %s via string mode", str(obj_hint), source)
            else:
                _re = re.compile(r".*%s.*" % obj_hint)
                _dbg = _re.findall(source)
                _logger.debug(_re.pattern)
                if _dbg:
                    _logger.debug(_dbg)

                if _re.match(source):
                    found = True
            if found:
                if _logger.isEnabledFor(logging.DEBUG):
                    _log_msg = ["Hint: %s" % obj_hint]
                    _temp = re.finditer(r"\b%s\b" % obj_hint, source)
                    for _o in _temp:
                        _log_msg += [repr(source)]
                        _log_msg += [' '*_o.start() + '^'*(_o.end() - _o.start())]

                    _logger.debug("The match is %s", source)
                    _logger.debug("\n".join(_log_msg))

                touch(source)
                build_source(libraries, source)
            else:
                _logger.fatal("Could not find %s" % str(obj_hint))
                if not Config.is_toolchain:
                    raise RuntimeError("Could not find %s" % str(obj_hint))
    if not found:
        print "** Warning: %s(1): Unable to find rebuild %s.%s" % (obj_hint, str(lib_name), obj_hint)

_DEPTH = 0

def build_source(libraries, source):
    global _DEPTH
    _DEPTH += 1
    _logger.info("Building %s", source)
    for lib in libraries.itervalues():
        for added_source in lib.get_sources():
            if os.path.abspath(added_source) == os.path.abspath(source):

                while True:
                    _logger.debug("######################## (%d) buliding %s", _DEPTH, source)
                    errors, warnings = lib.build_single(source, extra_flags=VCOM_BUILD_OPTS['single'])

                    rebuild_list = []
                    for error in errors:
                        _temp = _discover_recompiles(libraries, source, error)
                        if None not in _temp:
                            _logger.debug("Error %s added %s to the rebuild list", repr(error), str(_temp))
                            rebuild_list.append(_temp)

                    # if _DEPTH == 1:

                    if rebuild_list:
                        _logger.debug("Rebuild list: %s", str(rebuild_list))
                    for _, _hint in rebuild_list:
                        rebuild(libraries, _hint)
                    if len(rebuild_list) == 0:
                        if _DEPTH == 1:
                            for error in errors:
                                print error
                            for warning in warnings:
                                print warning
                        _DEPTH -= 1
                        return 0



                # lib.build_single(source,
                #     ['-explicit', '-defercheck', '-novopt', '-nocheck',
                #     '-pedantic', '-lint',
                #     '-lrmconfigvis',
                #     ]
                # )
                _DEPTH -= 1
                return 0
    _DEPTH -= 1
    return 1

def build_tags(libs):
    _threads = []

    tagfiles = []
    thread_cnt = 0
    for lib in libs.itervalues():
        _this_thread = threading.Thread(target=lib.build_tags)
        _this_thread.start()
        _threads.append(_this_thread)
        tagfiles.append(lib.tagfile)

        thread_cnt += 1
        if thread_cnt == Config.thread_limit:
            thread_cnt = 0
            for thread in _threads:
                thread.join()
            _threads = []
    for thread in _threads:
        thread.join()

    try:
        fd = open(CTAGS_VIM_CFG_FILE, 'w')
        fd.write(",".join(tagfiles))
        fd.close()
    except IOError:
        _logger.error("Unable to find CTAGs Vim config file at '%s'", CTAGS_VIM_CFG_FILE)



def search_makefiles():
    # return {'base_lib' : Library(makefile='src/base_lib/Makefile', build_at=TARGET_DIR)}

    libs = {}
    for directory in ('src', ):
        for makefile_path in find_files_in_path(directory, _is_makefile):
            this_lib = Library(makefile=makefile_path, build_at=TARGET_DIR)
            libs[this_lib.name] = this_lib
    return libs

def get_custom_libs():

    libs = {}

    work = Library(name='work', build_at=TARGET_DIR)
    for work_path in ('./test/m200_fase2/f1/xaw2vhd_dir/',
                      './src/m200_fase2/f1/',
                      # './src/m200_fase2/f2/',
                      './test/m200_fase2/simulation/',
                      './test/cpld_m200_fase2/',
                      './test/stc_ctrl_ip/',
                      './src/xaize_arch/',):
        if not os.path.exists(work_path):
            continue
        for f in find_files_in_path(work_path, _is_vhd, recursive=0):
            work.add_source(f)
    work.add_source('./src/cpld_m200_fase2/ram_dual_port.vhd')
    work.remove_source(lambda x : os.path.basename(x) == 'f1_test_iface_top.vhd')
    libs['work'] = work

    kryptus = Library(name='kryptus', build_at=TARGET_DIR)
    for _path in ('./src/onfi_noecc_ip/xrs_core',
                  './src/onfi_noecc_ip/axi_lib',
                  './src/onfi_noecc_ip/mem_lib',
                  './src/onfi_noecc_ip/plb_lib',
                  './src/onfi_noecc_ip',):
        for f in find_files_in_path(_path, _is_vhd, recursive=0):
            kryptus.add_source(f)
    libs['kryptus'] = kryptus


    uart_legado_ip = Library(name='uart_legado_ip', build_at=TARGET_DIR)
    _path = 'src/uart_legado_ip'
    for f in find_files_in_path(_path, _is_vhd, recursive=0):
        uart_legado_ip.add_source(f)
    libs['uart_legado_ip'] = uart_legado_ip

    ow_ip = Library(name='ow_ip', build_at=TARGET_DIR)
    _path = 'src/ow_ip'
    for f in find_files_in_path(_path, _is_vhd, recursive=0):
        ow_ip.add_source(f)
    libs['ow_ip'] = ow_ip

    i2c_master_ip = Library(name='i2c_master_ip', build_at=TARGET_DIR)
    _path = 'src/i2c_master_ip'
    for f in find_files_in_path(_path, _is_vhd, recursive=0):
        i2c_master_ip.add_source(f)
    libs['i2c_master_ip'] = i2c_master_ip

    aurora_8b10b_f1_ip = Library(name='aurora_8b10b_f1_ip', build_at=TARGET_DIR)
    _path = 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1'
    for f in find_files_in_path(_path, _is_vhd, recursive=0):
        aurora_8b10b_f1_ip.add_source(f)
    libs['aurora_8b10b_f1_ip'] = aurora_8b10b_f1_ip

    transp_aurora_f1 = Library(name='transp_aurora_f1', build_at=TARGET_DIR)
    _path = 'src/transp_aurora_f1'
    for f in find_files_in_path(_path, _is_vhd, recursive=0):
        transp_aurora_f1.add_source(f)
    libs['transp_aurora_f1'] = transp_aurora_f1

    altera_mf = Library(name='altera_mf', build_at=TARGET_DIR)
    for f in find_files_in_path('/opt/altera/11.1sp1/quartus/libraries/vhdl/altera_mf', _is_vhd, recursive=1):
        altera_mf.add_source(f)
    libs['altera_mf'] = altera_mf

    lpm = Library(name='lpm', build_at=TARGET_DIR)
    for f in find_files_in_path('/opt/altera/11.1sp1/quartus/libraries/vhdl/lpm', _is_vhd, recursive=1):
        lpm.add_source(f)
    libs['lpm'] = lpm

    maxii = Library(name='maxii', build_at=TARGET_DIR)
    for f in find_files_in_path('/opt/altera/11.1sp1/quartus/eda/sim_lib/', _is_vhd, recursive=1):
        if os.path.basename(f).lower().startswith('maxii'):
            maxii.add_source(f)

    libs['maxii'] = maxii

    for lib in libs.itervalues():
        lib.add_build_opts('-2008')

    return libs

def imported_from_prj():
    LIBS = (
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_system/ddr2_phy_dq_iob.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_system/ddr2_phy_dqs_iob.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_system/ddr2_phy_dm_iob.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_system/ddr2_phy_calib.vhd'),
        ('base_lib', 'src/base_lib/base_lib_pkg.vhd'),
        ('proc_common_v3_00_a', 'src/xilinx_common/proc_common_v3_00_a/family_support.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_aurora_pkg.vhd'),
        ('plb_lib', 'src/plb_lib/plb_lib_pkg.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_system/ddr2_usr_wr.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_system/ddr2_usr_rd.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_system/ddr2_usr_addr_fifo.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_system/ddr2_phy_write.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_system/ddr2_phy_io.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_system/ddr2_phy_init.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_system/ddr2_phy_ctl_io.vhd'),
        ('proc_common_v3_00_a', 'src/xilinx_common/proc_common_v3_00_a/proc_common_pkg.vhd'),
        ('proc_common_v3_00_a', 'src/xilinx_common/proc_common_v3_00_a/mux_onehot_f.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_aurora_pkg.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_valid_data_counter.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_storage_switch_control.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_storage_mux.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_storage_count_control.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_storage_ce_control.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_sideband_output.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_rx_ll_deframer.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_output_switch_control.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_output_mux.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_left_align_mux.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_left_align_control.vhd'),
        ('sync_lib', 'src/sync_lib/sync_lib_pkg.vhd'),
        ('sync_lib', 'src/sync_lib/syncr.vhd'),
        ('plb_v46_v1_05_a', 'src/plb_lib/plb_v46_v1_05_a/qual_request.vhd'),
        ('plb_v46_v1_05_a', 'src/plb_lib/plb_v46_v1_05_a/qual_priority.vhd'),
        ('fifo_lib', 'src/fifo_lib/fifo_lib_pkg.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_system/ddr2_usr_top.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_system/ddr2_phy_top.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_system/ddr2_ctrl.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/ddr2_ctrl_pkg.vhd'),
        ('base_lib', 'src/base_lib/generic_ram.vhd'),
        ('proc_common_v3_00_a', 'src/xilinx_common/proc_common_v3_00_a/pselect_f.vhd'),
        ('proc_common_v3_00_a', 'src/xilinx_common/proc_common_v3_00_a/or_muxcy_f.vhd'),
        ('proc_common_v3_00_a', 'src/xilinx_common/proc_common_v3_00_a/down_counter.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_valid_data_counter.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_storage_switch_control.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_storage_mux.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_storage_count_control.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_storage_ce_control.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_sideband_output.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_rx_ll_deframer.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_output_switch_control.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_output_mux.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_left_align_mux.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_left_align_control.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_tx_ll_datapath.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_tx_ll_control.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_sym_gen_4byte.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_sym_dec_4byte.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_rx_ll_pdu_datapath.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_lane_init_sm_4byte.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_idle_and_ver_gen.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_err_detect_4byte.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_chbond_count_dec_4byte.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_channel_init_sm.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_channel_err_detect.vhd'),
        ('sync_lib', 'src/sync_lib/det_up.vhd'),
        ('sync_lib', 'src/sync_lib/det_dn.vhd'),
        ('plb_v46_v1_05_a', 'src/plb_lib/plb_v46_v1_05_a/rr_select.vhd'),
        ('plb_v46_v1_05_a', 'src/plb_lib/plb_v46_v1_05_a/priority_encoder.vhd'),
        ('plb_v46_v1_05_a', 'src/plb_lib/plb_v46_v1_05_a/pend_request.vhd'),
        ('plb_v46_v1_05_a', 'src/plb_lib/plb_v46_v1_05_a/pending_priority.vhd'),
        ('plb_v46_v1_05_a', 'src/plb_lib/plb_v46_v1_05_a/or_bits.vhd'),
        ('plb_lib', 'src/plb_lib/plb_rwcomp.vhd'),
        ('plb_lib', 'src/plb_lib/plb_rwack.vhd'),
        ('plb_lib', 'src/plb_lib/plb_busy_gen.vhd'),
        ('kryptus', 'src/onfi_noecc_ip/mem_lib/mem_ram_1ck.vhd'),
        ('lnt_ip', 'src/lnt_ip/lnt_ip_pkg.vhd'),
        ('fifo_lib', 'src/fifo_lib/bus_fifo.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_system/ddr2_mem_if_top.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_tx_ll_datapath.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_tx_ll_control.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_tile.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_sym_gen.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_sym_dec.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_rx_ll_pdu_datapath.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_lane_init_sm.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_idle_and_ver_gen.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_err_detect.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_chbond_count_dec.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_channel_init_sm.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_channel_err_detect.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_tx_ll.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_tile.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_rx_ll.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_global_logic.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_aurora_lane_4byte.vhd'),
        ('sync_lib', 'src/sync_lib/sync_det_up.vhd'),
        ('sync_lib', 'src/sync_lib/sync_det_dn.vhd'),
        ('plb_lib', 'src/plb_lib/plb_wreg.vhd'),
        ('plb_v46_v1_05_a', 'src/plb_lib/plb_v46_v1_05_a/watchdog_timer.vhd'),
        ('plb_v46_v1_05_a', 'src/plb_lib/plb_v46_v1_05_a/plb_interrupt.vhd'),
        ('plb_v46_v1_05_a', 'src/plb_lib/plb_v46_v1_05_a/plb_arb_encoder.vhd'),
        ('plb_v46_v1_05_a', 'src/plb_lib/plb_v46_v1_05_a/or_gate.vhd'),
        ('plb_v46_v1_05_a', 'src/plb_lib/plb_v46_v1_05_a/muxed_signals.vhd'),
        ('plb_v46_v1_05_a', 'src/plb_lib/plb_v46_v1_05_a/gen_qual_req.vhd'),
        ('plb_v46_v1_05_a', 'src/plb_lib/plb_v46_v1_05_a/dcr_regs.vhd'),
        ('plb_v46_v1_05_a', 'src/plb_lib/plb_v46_v1_05_a/arb_control_sm.vhd'),
        ('plb_lib', 'src/plb_lib/plb_sig_gen.vhd'),
        ('plb_lib', 'src/plb_lib/plb_sampler.vhd'),
        ('plb_lib', 'src/plb_lib/plb_rreg.vhd'),
        ('plb_lib', 'src/plb_lib/plb_int_addr_ack_gen.vhd'),
        ('plb_lib', 'src/plb_lib/plb_distributed_ram.vhd'),
        ('plb_lib', 'src/plb_lib/plb_addr_ack_gen.vhd'),
        ('ow_ip', 'src/ow_ip/ow_pkg.vhd'),
        ('kryptus', 'src/onfi_noecc_ip/plb_lib/plb_pkg.vhd'),
        ('kryptus', 'src/onfi_noecc_ip/mem_lib/mem_pkg.vhd'),
        ('kryptus', 'src/onfi_noecc_ip/mem_lib/mem_fifo_1ck.vhd'),
        ('kryptus', 'src/onfi_noecc_ip/axi_lib/axi_stream_pkg.vhd'),
        ('lnt_ip', 'src/lnt_ip/hamming_enc.vhd'),
        ('fifo_lib', 'src/fifo_lib/generic_fifo.vhd'),
        ('fifo_lib', 'src/fifo_lib/axi_stream_fifo.vhd'),
        ('dsp_lib', 'src/dsp_lib/dsp_lib_pkg.vhd'),
        ('dsp_lib', 'src/dsp_lib/axi_sub.vhd'),
        ('dsp_lib', 'src/dsp_lib/axi_mult.vhd'),
        ('dsp_lib', 'src/dsp_lib/axi_add.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_system/ddr2_top.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_system/ddr2_infrastructure.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_system/ddr2_chipscope.vhd'),
        ('base_lib', 'src/base_lib/sr_delay.vhd'),
        ('base_lib', 'src/base_lib/dco.vhd'),
        ('base_lib', 'src/base_lib/crc32_gen.vhd'),
        ('axi_stream_lib', 'src/axi_stream_lib/axi_stream_lib_pkg.vhd'),
        ('axi_stream_lib', 'src/axi_stream_lib/axi_stream_delay.vhd'),
        ('uart_legado_ip', 'src/uart_legado_ip/uart_legado_tx.vhd'),
        ('uart_legado_ip', 'src/uart_legado_ip/uart_legado_rx.vhd'),
        ('uart_legado_ip', 'src/uart_legado_ip/uart_legado_ip_pkg.vhd'),
        ('uart_legado_ip', 'src/uart_legado_ip/uart_baud_rate.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_tx_ll.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_transceiver_wrapper.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_rx_ll.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_global_logic.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_aurora_lane.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_transceiver_wrapper.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_standard_cc_module.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_reset_logic.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_clock_module.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_block.vhd'),
        ('sync_lib', 'src/sync_lib/sync_det_ud.vhd'),
        ('sync_lib', 'src/sync_lib/pulse_stretcher.vhd'),
        ('sync_lib', 'src/sync_lib/edge_detector.vhd'),
        ('stc_ctrl_ip', 'src/stc_ctrl_ip/stc_data_ctrl.vhd'),
        ('stc_ctrl_ip', 'src/stc_ctrl_ip/stc_ctrl_ip_pkg.vhd'),
        ('stc_ctrl_ip', 'src/stc_ctrl_ip/mem_axi_din.vhd'),
        ('spos_lib', 'src/spos_lib/spos_lib_pkg.vhd'),
        ('spos_f1f2_ip', 'src/spos_f1f2_ip/spos_f1f2_ip_pkg.vhd'),
        ('spos_f1f2_ip', 'src/spos_f1f2_ip/plb_tx_framer.vhd'),
        ('spos_f1f2_ip', 'src/spos_f1f2_ip/plb_rx_framer.vhd'),
        ('spi_master_ip', 'src/spi_master_ip/spi_master_pkg.vhd'),
        ('spi_master_axi_ip', 'src/spi_master_axi_ip/spi_master_core_axi.vhd'),
        ('spi_master_axi_ip', 'src/spi_master_axi_ip/spi_master_axi_ip_pkg.vhd'),
        ('rx_infra_lib', 'src/rx_infra/rx_infra_wr_encoder.vhd'),
        ('rx_infra_lib', 'src/rx_infra/rx_infra_read_req.vhd'),
        ('rx_infra_lib', 'src/rx_infra/rx_infra_read_pckt.vhd'),
        ('rx_infra_lib', 'src/rx_infra/rx_infra_read_ctrl.vhd'),
        ('rx_infra_lib', 'src/rx_infra/rx_infra_lib_pkg.vhd'),
        ('rx_infra_lib', 'src/rx_infra/rx_infra_adrs_gen.vhd'),
        ('router_m200_ip', 'src/router_m200_ip/router_core_pkg.vhd'),
        ('plb_lib', 'src/plb_lib/plb_write_cache.vhd'),
        ('plb_v46_v1_05_a', 'src/plb_lib/plb_v46_v1_05_a/plb_wr_datapath.vhd'),
        ('plb_v46_v1_05_a', 'src/plb_lib/plb_v46_v1_05_a/plb_slave_ors.vhd'),
        ('plb_v46_v1_05_a', 'src/plb_lib/plb_v46_v1_05_a/plb_rd_datapath.vhd'),
        ('plb_v46_v1_05_a', 'src/plb_lib/plb_v46_v1_05_a/plb_p2p.vhd'),
        ('plb_v46_v1_05_a', 'src/plb_lib/plb_v46_v1_05_a/plb_arbiter_logic.vhd'),
        ('plb_v46_v1_05_a', 'src/plb_lib/plb_v46_v1_05_a/plb_addrpath.vhd'),
        ('plb_lib', 'src/plb_lib/plb_sticky.vhd'),
        ('plb_lib', 'src/plb_lib/plb_regbank.vhd'),
        ('plb_lib', 'src/plb_lib/plb_read_cache.vhd'),
        ('plb_lib', 'src/plb_lib/plb_pulse.vhd'),
        ('ow_ip', 'src/ow_ip/ow_search.vhd'),
        ('kryptus', 'src/onfi_noecc_ip/xrs_core/xrs_core_pkg.vhd'),
        ('kryptus', 'src/onfi_noecc_ip/plb_lib/plb_slave.vhd'),
        ('kryptus', 'src/onfi_noecc_ip/onfi_flash_pkg.vhd'),
        ('kryptus', 'src/onfi_noecc_ip/axi_lib/axi_stream_slave.vhd'),
        ('kryptus', 'src/onfi_noecc_ip/axi_lib/axi_stream_master.vhd'),
        ('work', 'src/m200_fase2/f1/gtx_teste_tile.vhd'),
        ('lnt_ip', 'src/lnt_ip/roff_ctl.vhd'),
        ('lnt_ip', 'src/lnt_ip/mem_ctl.vhd'),
        ('lnt_ip', 'src/lnt_ip/lpln_master.vhd'),
        ('lnt_ip', 'src/lnt_ip/fase2_roff_ctl.vhd'),
        ('framer_deframer_ip', 'src/framer_deframer_ip/framer_deframer_pkg.vhd'),
        ('fifo_lib', 'src/fifo_lib/axi_pckt_fifo.vhd'),
        ('dsp_lib', 'src/dsp_lib/axi_ram.vhd'),
        ('dsp_lib', 'src/dsp_lib/axi_cmult.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_system/mig.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_plb_plb.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_plb_core.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_ctrl_axi.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_arb_priority_ctrl.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_arb_demux.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_arb_buffer.vhd'),
        ('base_lib', 'src/base_lib/crc32_check.vhd'),
        ('axi_stream_lib', 'src/axi_stream_lib/axi_wr_ddr2.vhd'),
        ('axi_stream_lib', 'src/axi_stream_lib/axi_stream_merge.vhd'),
        ('axi_stream_lib', 'src/axi_stream_lib/axi_rm_last_word.vhd'),
        ('axi_stream_lib', 'src/axi_stream_lib/axi_pckt_frag.vhd'),
        ('axi_stream_lib', 'src/axi_stream_lib/axi_mux_select.vhd'),
        ('axi_stream_lib', 'src/axi_stream_lib/axi_demux.vhd'),
        ('work', '/home/asouto/git-svn/odf/branches/fea-13666/fpga/test/m200_fase2/f1/xaw2vhd_dir/pll_refclk.vhd'),
        ('work', '/home/asouto/git-svn/odf/branches/fea-13666/fpga/test/m200_fase2/f1/xaw2vhd_dir/aur_dcm.vhd'),
        ('work', '/home/asouto/git-svn/odf/branches/fea-13666/fpga/test/m200_fase2/f1/xaw2vhd_dir/aurora_dcm.vhd'),
        ('uart_legado_ip', 'src/uart_legado_ip/uart_legado_plb.vhd'),
        ('uart_legado_ip', 'src/uart_legado_ip/uart_legado_core.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora_standard_cc_module.vhd'),
        ('transp_aurora_f1', 'src/transp_aurora_f1/transp_aurora.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_top.vhd'),
        ('aurora_8b10b_f1_ip', 'src/transp_aurora_8b10b/ipcore_dir/aurora_8b10b_1lane_f1/aurora_8b10b_f1_pkg.vhd'),
        ('sync_fsm_ip', 'src/sync_fsm_ip/timer_syncr.vhd'),
        ('sync_fsm_ip', 'src/sync_fsm_ip/sync_pulse_to_ll.vhd'),
        ('sync_fsm_ip', 'src/sync_fsm_ip/sync_io_convert.vhd'),
        ('sync_fsm_ip', 'src/sync_fsm_ip/sync_fsm_pkg.vhd'),
        ('sync_fsm_ip', 'src/sync_fsm_ip/so_sync_fsm.vhd'),
        ('stc_ctrl_ip', 'src/stc_ctrl_ip/stc_varsize_spi.vhd'),
        ('stc_ctrl_ip', 'src/stc_ctrl_ip/stc_varsize_proc.vhd'),
        ('spos_lib', 'src/spos_lib/spos_dac_iface_f1_plb.vhd'),
        ('spos_lib', 'src/spos_lib/spos_dac_iface_f1.vhd'),
        ('spos_lib', 'src/spos_lib/spos_adc_to_axi.vhd'),
        ('spos_lib', 'src/spos_lib/spos_adc_iface_f1_plb.vhd'),
        ('spos_lib', 'src/spos_lib/spos_adc_iface_f1.vhd'),
        ('spos_f1f2_ip', 'src/spos_f1f2_ip/plb_framer.vhd'),
        ('spos_f1f2_ip', 'src/spos_f1f2_ip/inter_fpga_plb_slave.vhd'),
        ('spos_f1f2_ip', 'src/spos_f1f2_ip/gtx_alignment_ctrl.vhd'),
        ('spi_master_ip', 'src/spi_master_ip/spi_master_plb.vhd'),
        ('spi_master_ip', 'src/spi_master_ip/spi_master_core.vhd'),
        ('rx_infra_lib', 'src/rx_infra/rx_infra_read_req_64.vhd'),
        ('rx_infra_lib', 'src/rx_infra/rx_infra_read_pckt_64.vhd'),
        ('rx_infra_lib', 'src/rx_infra/rx_infra_core.vhd'),
        ('rx_infra_lib', 'src/rx_infra/rx_infra_adc_framer.vhd'),
        ('rx_infra_lib', 'src/rx_infra/extract_header_64.vhd'),
        ('rx_infra_lib', 'src/rx_infra/extract_header.vhd'),
        ('router_m200_ip', 'src/router_m200_ip/router_plb.vhd'),
        ('router_m200_ip', 'src/router_m200_ip/router_core.vhd'),
        ('plb_lib', 'src/plb_lib/plb_vector_range_detector.vhd'),
        ('plb_v46_v1_05_a', 'src/plb_lib/plb_v46_v1_05_a/plb_v46.vhd'),
        ('plb_lib', 'src/plb_lib/plb_sticky_bus.vhd'),
        ('ow_ip', 'src/ow_ip/ow_plb.vhd'),
        ('ow_ip', 'src/ow_ip/ow_core.vhd'),
        ('output_timer_ip', 'src/output_timer_ip/output_timer_ip_pkg.vhd'),
        ('output_timer_ip', 'src/output_timer_ip/output_timer.vhd'),
        ('kryptus', 'src/onfi_noecc_ip/onfi_flash_plb.vhd'),
        ('kryptus', 'src/onfi_noecc_ip/onfi_flash_cycle.vhd'),
        ('kryptus', 'src/onfi_noecc_ip/onfi_flash_cmd.vhd'),
        ('kryptus', 'src/onfi_noecc_ip/onfi_flash_axi.vhd'),
        ('work', 'src/m200_fase2/f1/gtx_teste.vhd'),
        ('work', 'src/m200_fase2/f1/f1_m200_fase2_pkg.vhd'),
        ('lnt_ip', 'src/lnt_ip/lnt_master_core.vhd'),
        ('lnt_ip', 'src/lnt_ip/lnt_axi_iface.vhd'),
        ('lnt_ip', 'src/lnt_ip/fase2_lnt_master_core.vhd'),
        ('i2c_master_ip', 'src/i2c_master_ip/i2c_master_plb.vhd'),
        ('i2c_master_ip', 'src/i2c_master_ip/i2c_master_pkg.vhd'),
        ('i2c_master_ip', 'src/i2c_master_ip/i2c_master_core.vhd'),
        ('framer_deframer_ip', 'src/framer_deframer_ip/framer.vhd'),
        ('framer_deframer_ip', 'src/framer_deframer_ip/deframer.vhd'),
        ('dsp_lib', 'src/dsp_lib/smooth_filter.vhd'),
        ('dsp_lib', 'src/dsp_lib/axi_truncate.vhd'),
        ('dsp_lib', 'src/dsp_lib/axi_three_add.vhd'),
        ('dsp_lib', 'src/dsp_lib/axi_decimation.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_wrapper.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_plb_top.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_axi_top.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_axi64_top.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/mig_arb_top.vhd'),
        ('ddc_m200_ip', 'src/ddc_m200_ip/ddc_m200_pkg.vhd'),
        ('ddc_m200_ip', 'src/ddc_m200_ip/clut_mult.vhd'),
        ('config_fpga2_lib', 'src/config_fpga2/config_fpga2_lib_pkg.vhd'),
        ('config_fpga2_lib', 'src/config_fpga2/axi_config_data.vhd'),
        ('check_lib', 'src/check_lib/check_lib_pkg.vhd'),
        ('base_lib', 'src/base_lib/release_info_pkg.vhd'),
        ('base_lib', 'src/base_lib/decimation.vhd'),
        ('axi_stream_lib', 'src/axi_stream_lib/ll_to_axi.vhd'),
        ('axi_stream_lib', 'src/axi_stream_lib/lldma_to_axi.vhd'),
        ('axi_stream_lib', 'src/axi_stream_lib/axi_to_ll.vhd'),
        ('axi_stream_lib', 'src/axi_stream_lib/axi_merge.vhd'),
        ('apd_lib', 'src/apd_lib/apd_slave.vhd'),
        ('apd_lib', 'src/apd_lib/apd_lib_pkg.vhd'),
        ('uart_legado_ip', 'src/uart_legado_ip/uart_legado_top.vhd'),
        ('sync_fsm_ip', 'src/sync_fsm_ip/sync_wire_top.vhd'),
        ('sum_m200_ip', 'src/sum_m200_ip/sum_m200_pkg.vhd'),
        ('sum_m200_ip', 'src/sum_m200_ip/sum_m200.vhd'),
        ('stc_ctrl_ip', 'src/stc_ctrl_ip/stc_ctrl_top_m200.vhd'),
        ('spos_lib', 'src/spos_lib/spos_dac_iface_f1_top.vhd'),
        ('spos_lib', 'src/spos_lib/spos_adc_iface_f1_top.vhd'),
        ('spi_master_ip', 'src/spi_master_ip/spi_master_top.vhd'),
        ('rx_infra_lib', 'src/rx_infra/rx_infra_top.vhd'),
        ('router_m200_ip', 'src/router_m200_ip/router_top.vhd'),
        ('plb_lib', 'src/plb_lib/plb_v46_wrapper.vhd'),
        ('ow_ip', 'src/ow_ip/ow_top.vhd'),
        ('output_timer_ip', 'src/output_timer_ip/axi_timer_top.vhd'),
        ('kryptus', 'src/onfi_noecc_ip/onfi_flash_core.vhd'),
        ('work', 'src/m200_fase2/f1/tx_protection.vhd'),
        ('work', 'src/m200_fase2/f1/f1_test_plb.vhd'),
        ('work', 'src/m200_fase2/f1/f1_inter_fpga_bridge.vhd'),
        ('work', 'src/m200_fase2/f1/f1_dsp_regbank.vhd'),
        ('work', 'src/m200_fase2/f1/f1_clock_wrapper.vhd'),
        ('work', 'src/m200_fase2/f1/f1_aurora_wrapper.vhd'),
        ('work', 'src/m200_fase2/f1/f1_aurora_raw_wrapper.vhd'),
        ('work', 'src/m200_fase2/f1/digio_f1_sync_bplb.vhd'),
        ('work', 'src/m200_fase2/f1/digio_f1_old_board.vhd'),
        ('work', 'src/m200_fase2/f1/digio_f1.vhd'),
        ('work', 'src/m200_fase2/f1/config_f2_wrapper.vhd'),
        ('work', 'src/m200_fase2/f1/beam_ctrl.vhd'),
        ('lnt_ip', 'src/lnt_ip/axi_lnt_top.vhd'),
        ('i2c_master_ip', 'src/i2c_master_ip/i2c_master_top.vhd'),
        ('framer_deframer_ip', 'src/framer_deframer_ip/framer_deframer.vhd'),
        ('ddr2_ctrl_ip', 'src/ddr2_ctrl_ip/ddr2_ctrl_top.vhd'),
        ('ddc_m200_ip', 'src/ddc_m200_ip/ddc_m200.vhd'),
        ('axi_tx_infra_lib', 'src/axi_tx_infra/axi_tx_infra_pkg.vhd'),
        ('axi_stream_lib', 'src/axi_stream_lib/axi_stream_duplicate.vhd'),
        ('axi_stream_lib', 'src/axi_stream_lib/axi_concatenate.vhd'),
        ('work', 'src/m200_fase2/f1/f1_m200_fase2_top.vhd'),
    )

    libs = {}
    for lib, source in LIBS:
        if lib not in libs.keys():
            libs[lib] = Library(name=lib, build_at=TARGET_DIR)
        libs[lib].add_source(source)


    for source in find_files_in_path('test/m200_fase2/simulation/', _is_vhd):
        libs['work'].add_source(source)

    return libs

LOCK_FILE = '/tmp/vhd_builder.lock'

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--build-ctags',        '-t',                action='store_true')
    parser.add_argument('--build-source',       '-c',                action='store')
    parser.add_argument('--build-until-stable', '-f',                action='store_true')
    parser.add_argument('--thread-limit',       action='store',      type=int)
    #  parser.add_argument('--silent',             action='store_true', default=False)
    args = parser.parse_args()

    Config.updateFromArgparse(args)

    libraries = {}
    libraries.update(search_makefiles())
    libraries.update(get_custom_libs())

    # libraries = imported_from_prj()

    if Config.build_ctags:
        tags_t = threading.Thread(target=build_tags, args=(libraries,))
        tags_t.start()

    if Config.silent:
        verbose = False
    else:
        verbose = True
    if Config.build_until_stable:
        build_until_stable(libraries, verbose)

    if Config.build_source:
        _logger.debug("Searching for '%s'", Config.build_source)
        if build_source(libraries, Config.build_source):
            _logger.warning("Unable to find source file '%s'", Config.build_source)
            print "** Warning: %s(1): Unable to find source file" % Config.build_source

    if Config.build_ctags:
        tags_t.join()


class Config(object):
    is_toolchain = True
    silent = True
    thread_limit = 20

    @staticmethod
    def _setupStreamHandler(stream):
        stream_handler = logging.StreamHandler(stream)
        stream_handler.formatter = logging.Formatter(_LOG_FORMAT)
        logging.root.addHandler(stream_handler)
        logging.root.setLevel(_LOG_LEVEL)
        #  _logger.addHandler(stream_handler)
        #  _logger_vcom.addHandler(stream_handler)

    @staticmethod
    def _setupFileHandler(f):
        file_handler = logging.FileHandler(f)
        file_handler.formatter = logging.Formatter(_LOG_FORMAT)
        logging.root.addHandler(file_handler)
        logging.root.setLevel(_LOG_LEVEL)
        #  _logger.addHandler(file_handler)
        #  _logger_vcom.addHandler(file_handler)

    @staticmethod
    def _setupToolchain():
        Config._setupFileHandler(_LOG_FILE)
        _logger.info("Setup for toolchain")
        Config.is_toolchain = True
        Config.silent = True

    @staticmethod
    def _setupStandalone():
        Config._setupStreamHandler(sys.stdout)
        _logger.info("Setup for standalone")
        Config.is_toolchain = False
        Config.silent = False

    @staticmethod
    def setupBuild():
        if 'VIM' in os.environ.keys():
            Config.is_toolchain = True
            Config._setupToolchain()
        else:
            Config.is_toolchain = False
            Config._setupStandalone()

    @staticmethod
    def updateFromArgparse(args):
        for k, v in args._get_kwargs():
            if k in ('is_toolchain', ):
                raise RuntimeError("Can't redefine %s" % k)

            if k == 'thread_limit' and v is None:
                continue

            setattr(Config, k, v)

        _msg = ["Configuration update"]
        for k, v in Config.getCurrentConfig().iteritems():
            _msg += ["%s = %s" % (str(k), str(v))]

        _logger.info("\n".join(_msg))

    @staticmethod
    def getCurrentConfig():
        r = {}
        for k, v in Config.__dict__.iteritems():
            if k.startswith('_'):
                continue
            if k.startswith('__') and k.startswith('__'):
                continue
            if type(v) is staticmethod:
                continue
            r[k] = v
        return r

if __name__ == '__main__':
    Config.setupBuild()

    if os.path.exists(LOCK_FILE):
        print "Project build is still running..."
    else:
        import time
        start = time.time()
        touch(LOCK_FILE)
        try:
            read_makefile_cache()
            main()
            write_makefile_cache()
        finally:
            os.remove(LOCK_FILE)
        end = time.time()
        _logger.info("Build took %.2fs" % (end - start))

