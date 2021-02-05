DESTDIR ?= /
moduledir ?= $(DESTDIR)/usr/share/mender/modules/v3
inventorydir ?= $(DESTDIR)/usr/share/mender/inventory

# No-op for this project
build:

# "check" is standard is autotools projects, make an alias.
check: test

test:
	$(MAKE) -C tests test

install:
	install -d -m 755 $(moduledir)
	install -m 755 src/mender-configure $(moduledir)/

	install -d -m 755 $(inventorydir)
	install -m 755 src/mender-inventory-mender-configure $(inventorydir)/

uninstall:
	rm -f $(moduledir)/mender-configure
	rmdir -p --ignore-fail-on-non-empty $(moduledir)

	rm -f $(inventorydir)/mender-inventory-mender-configure
	rmdir -p --ignore-fail-on-non-empty $(inventorydir)

.PHONY: build
.PHONY: check
.PHONY: install
.PHONY: test
.PHONY: uninstall
