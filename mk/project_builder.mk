include ./mk/msim-options.mk
SHELL := /bin/bash

ifdef VIM
BG_ARGS := 2>&1 &
else
BG_ARGS :=
endif

ifdef THREADS
THREAD_ARGS := --thread-limit $(THREADS)
endif

clean:
	$(RM) -rf .build/
	$(RM) -rf modelsim.ini

build: .vcom
	project_builder.py --build-ctags $(THREAD_ARGS) --build-until-stable $(BG_ARGS)
	# project_builder.py --build-ctags $(THREAD_ARGS) --build-until-stable --silent 2>&1 &

rebuild: clean build

ifneq ($(wildcard .build/*),)
$(addprefix rebuild-,$(shell find .build/ -maxdepth 1 -type d  | cut -d '/' -f2 2>&1)):
	$(eval TARGET_LIB=$(patsubst rebuild-%,%,$@))
	$(RM) -r .build/$(TARGET_LIB)
	$(MAKE) $(MFLAGS) build

.rebuild:
	@echo "Not rebuilding"

%.vhd: .vcom
	project_builder.py --build-ctags $(THREAD_ARGS) --build-source $@

else

%.vhd: .vcom
	project_builder.py --build-ctags $(THREAD_ARGS) --build-until-stable --build-source $@  2>&1 &

endif
	
.vcom:
	@which vcom > /dev/null

