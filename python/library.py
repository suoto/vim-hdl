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

import os, logging

from utils import shell

class Library(object):

    MODELSIM_INI_PATH = 'modelsim.ini'

    def __init__(self, **kwargs):
        self.name = kwargs.get('name', None)

        self.build_location = kwargs.get('build_location')
        self.tagfile = os.path.join(self.build_location, self.name + '.tags')

        self._extra_flags = []
        self._sources = []
        self._logger = logging.getLogger("Library('%s')" % self.name)

        self._logger.debug("Creating library with parms %s", kwargs)

        self._compiled = []
        self._failed = []

        self._create_library()

    def __str__(self):
        return "Library(name='%s', build_location='%s')" % (self.name, self.build_location)

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
        return self._sources

    def _create_library(self):
        lib_path = os.path.sep.join([self.build_location, self.name])
        if os.path.exists(os.path.sep.join([lib_path, '_info'])):
            self._logger.debug("Library '%s' already exists at '%s', returning", self.name, lib_path)
            return

        self._logger.debug("Creating library '%s' at '%s'", self.name, lib_path)
        if not os.path.exists(self.MODELSIM_INI_PATH):
            self._logger.debug("[%s] Creating lib without modelsim.ini at %s", self.name, self.build_location)
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
        lib_path = os.path.sep.join([self.build_location, self.name])

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
            #  append_to_compile_order_file(self.name, source)
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
        lib_path = os.path.sep.join([self.build_location, self.name])

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
                    #  append_to_compile_order_file(self.name, source)


            # print warning

            # if sts == 0:
            #     if source not in self._compiled:
            #         self._compiled.append(source)
            #     if source in self._failed:
            #         self._failed.remove(source)
            #     touch(ref_file)
            #     append_to_compile_order_file(self.name, source)
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
        lib_path = os.path.sep.join([self.build_location, self.name])
        ref_file = os.path.sep.join([lib_path, "." + os.path.basename(source)]) + ".ran_vcom"
        touch(ref_file)
        #  append_to_compile_order_file(self.name, source)
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
        lib_path = os.path.sep.join([self.build_location, self.name])
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

