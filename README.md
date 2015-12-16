# vim-hdl

vim-hdl is a Vim plugin that provides some helpers to VHDL development:

* Syntax checking (using
  [third-party-compilers](#supported-third-party-compilers) +
  [Syntastic][Syntastic])
* [Style checking](#style-checking)

![vim-hdl screenshot](http://i.imgur.com/YksSZq0.png)

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

## Usage

vim-hdl requires a configuration file listing libraries, source files,
build flags, etc. Select the configuration file via

```viml
let g:vimhdl_conf_file = '<config/file>'
```

See the [wiki](https://github.com/suoto/vim-hdl/wiki#project-file-formats) for
details on how to write it.

Any other [Syntastic][Syntastic] option should work as well.

You can clone [vim-hdl-examples][vim-hdl-examples] repository and try a ready-to-use
setup.

## Supported third-party compilers

* [Mentor Graphics® ModelSim®][Mentor_msim]
* [ModelSim-Altera® Edition][Altera_msim]

Tools with experimental support:

* Xilinx XVHDL (bundled with [Vivado][Xilinx_Vivado], including the WebPACK edition)

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

## Issues

You can use the [issue tracker][issue_tracker] for bugs, feature request and so on.

Tags support was dropped as there are [many better alternatives][ctags-alternatives]
not tied to a configuration file.

## License

This software is licensed under the [GPL v3 license][gpl].

## Notice

Mentor Graphics®, ModelSim® and their respective logos are trademarks or registered
trademarks of Mentor Graphics, Inc.

Altera® and its logo is a trademark or registered trademark of Altera Corporation.

Xilinx® and its logo is a trademark or registered trademark of Xilinx, Inc.

vim-hdl's author has no connection or affiliation to any of the trademarks mentioned
or used by this software.

[Syntastic]: https://github.com/scrooloose/syntastic
[Mentor_msim]: http://www.mentor.com/products/fv/modelsim/
[Altera_msim]: https://www.altera.com/downloads/download-center.html
[Xilinx_Vivado]: http://www.xilinx.com/products/design-tools/vivado/vivado-webpack.html
[pathogen]: https://github.com/tpope/vim-pathogen
[vundle]: https://github.com/VundleVim/Vundle.vim
[ConfigParser]: https://docs.python.org/2/library/configparser.html
[vim-hdl-examples]: https://github.com/suoto/vim-hdl-examples
[gpl]: http://www.gnu.org/copyleft/gpl.html
[issue_tracker]: https://github.com/suoto/vim-hdl/issues
[ctags-alternatives]: https://github.com/search?l=VimL&q=vim+ctags&ref=searchresults&type=Repositories&utf8=%E2%9C%93
