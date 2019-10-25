# vim-hdl

## May I have your attention please?

**[HDL Checker][hdl_checker] implements the core functionality of `vim-hdl` and
because it now supports [Language Server Protocol][LSP], `vim-hdl` is being
deprecated**

### How to continue using HDL Checker

Any [LSP client][LSP_clients] should work, be it on Vim or other editors.

Have a look at [HDL Checker supported editors][hdl_checker_editor_support] to
check some examples of how to set it up.

### But I want to keep using Syntastic!

You'll need to install HDL Checker pip package:

```
pip install hdl-checker --upgrade
```

or

```
pip install hdl-checker --upgrade --user
```

Just make sure you can run `hdl_checker --version` and it should work just fine.

### Rationale

Back when vim-hdl started, Vim did not have the widespread support for LSP it has
today and with it I can actually focus in the core functionality and support more
platforms at the same time. This last update is likely the last one!

---

[![Build Status](https://travis-ci.org/suoto/vim-hdl.svg?branch=master)](https://travis-ci.org/suoto/vim-hdl)
[![codecov](https://codecov.io/gh/suoto/vim-hdl/branch/master/graph/badge.svg)](https://codecov.io/gh/suoto/vim-hdl)
[![Join the chat at https://gitter.im/suoto/vim-hdl](https://badges.gitter.im/suoto/vim-hdl.svg)](https://gitter.im/suoto/vim-hdl?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
[![Analytics](https://ga-beacon.appspot.com/UA-68153177-3/vim-hdl/README.md?pixel)](https://github.com/suoto/vim-hdl)

vim-hdl is a Vim plugin that uses [HDL Checker][hdl_checker] to provide some
helpers to VHDL development:

* Syntax checking (using
  [third-party-compilers](#supported-third-party-compilers) +
  [Syntastic][Syntastic])
* [Style checking](#style-checking)

---

![vim-hdl screenshot](http://i.imgur.com/2hZox5r.gif)

---

## Installation

### [Pathogen][pathogen]

```bash
cd ~/.vim/bundle/
git clone https://github.com/suoto/vim-hdl.git
```

### [Vundle][vundle]

In your .vimrc:

```viml
Plugin 'suoto/vim-hdl'
```

### Notes

* Requires Vim compiled with Python support, plus features needed by
  [Syntastic][Syntastic] itself
* Only tested on Linux with recent Vim versions (7.4+)

---

## Usage

vim-hdl requires a configuration file listing libraries, source files, build
flags, etc. Select the configuration file via

```viml
" Configure the project file
let g:vimhdl_conf_file = '<config/file>'
```

You use the `VimhdlCreateProjectFile` command to search and help you setting up
the configuration file

```viml
:VimhdlCreateProjectFile <optional/path/to/files>
```

See the [wiki](https://github.com/suoto/hdl_checker/wiki) for details on how to write
it.

Any other [Syntastic][Syntastic] option should work as well.

You can clone [vim-hdl-examples][vim-hdl-examples] repository and try a ready to
use setup.

---

## Supported third-party compilers

* [Mentor Graphics® ModelSim®][Mentor_msim]
* [ModelSim-Altera® Edition][Altera_msim]
* [GHDL][GHDL]

---

## Style checking

Style checks are independent of a third-party compiler. Checking includes:

* Signal names in lower case
* Constants and generics in upper case
* Unused signals, constants, generics, shared variables, libraries, types and
  attributes
* Comment tags (`FIXME`, `TODO`, `XXX`)

Notice that currently the unused reports has caveats, namely declarations with
the same name inherited from a component, function, procedure, etc. In the
following example, the signal `rdy` won't be reported as unused in spite of the
fact it is not used.

```vhdl
signal rdy, refclk, rst : std_logic;
...

idelay_ctrl_u : idelay_ctrl
    port map (rdy    => open,
              refclk => refclk,
              rst    => rst);
```

---

## Issues

* [vim-hdl issue tracker][vimhdl_issue_tracker] should be used for bugs, feature
  requests, etc related to the Vim client itself (something that only happens
  with Vim)
* [HDL Checker issue tracker][hdl_checker_issue_tracker] should be used for bugs,
  feature requests, etc related to the code checker backend.

If unsure, use [vim-hdl issue tracker][vimhdl_issue_tracker], it will be moved to
[HDL Checker issue tracker][hdl_checker_issue_tracker] if applicable.

## License

This software is licensed under the [GPL v3 license][gpl].

## Notice

Mentor Graphics®, ModelSim® and their respective logos are trademarks or
registered trademarks of Mentor Graphics, Inc.

Altera® and its logo is a trademark or registered trademark of Altera
Corporation.

Xilinx® and its logo is a trademark or registered trademark of Xilinx, Inc.

vim-hdl's author has no connection or affiliation to any of the trademarks
mentioned or used by this software.

[Altera_msim]: https://www.altera.com/downloads/download-center.html
[ConfigParser]: https://docs.python.org/2/library/configparser.html
[GHDL]: https://github.com/tgingold/ghdl
[gpl]: http://www.gnu.org/copyleft/gpl.html
[hdl_checker]: https://github.com/suoto/hdl_checker
[hdl_checker_editor_support]: https://github.com/suoto/hdl_checker#editor-support
[hdl_checker_issue_tracker]: https://github.com/suoto/hdl_checker/issues
[LSP]: https://en.wikipedia.org/wiki/Language_Server_Protocol
[Mentor_msim]: http://www.mentor.com/products/fv/modelsim/
[pathogen]: https://github.com/tpope/vim-pathogen
[Syntastic]: https://github.com/scrooloose/syntastic
[vim-hdl-examples]: https://github.com/suoto/vim-hdl-examples
[vimhdl_issue_tracker]: https://github.com/suoto/vim-hdl/issues
[vundle]: https://github.com/VundleVim/Vundle.vim
[Xilinx_Vivado]: http://www.xilinx.com/products/design-tools/vivado/vivado-webpack.html
[LSP_clients]: https://microsoft.github.io/language-server-protocol/implementors/tools/
