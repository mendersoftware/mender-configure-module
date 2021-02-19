DESTDIR ?= /
moduledir ?= $(DESTDIR)/usr/share/mender/modules/v3
inventorydir ?= $(DESTDIR)/usr/share/mender/inventory

# No-op for this project
build:

# "check" is standard is autotools projects, make an alias.
check: test

test:
	$(MAKE) -C tests test

install: install-bin install-systemd

install-bin:
	install -d -m 755 $(moduledir)
	install -m 755 src/mender-configure $(moduledir)/

	install -d -m 755 $(inventorydir)
	install -m 755 src/mender-inventory-mender-configure $(inventorydir)/

install-systemd:
	install -d -m 755 $(DESTDIR)/lib/systemd/system
	install -m 644 support/mender-configure-apply-device-config.service $(DESTDIR)/lib/systemd/system/

uninstall: uninstall-bin uninstall-systemd

uninstall-bin:
	rm -f $(moduledir)/mender-configure
	rmdir -p --ignore-fail-on-non-empty $(moduledir)

	rm -f $(inventorydir)/mender-inventory-mender-configure
	rmdir -p --ignore-fail-on-non-empty $(inventorydir)

uninstall-systemd:
	rm -f $(DESTDIR)/lib/systemd/system/mender-configure-apply-device-config.service
	rmdir -p --ignore-fail-on-non-empty $(DESTDIR)/lib/systemd/system

.PHONY: build
.PHONY: check
.PHONY: install
.PHONY: install-bin
.PHONY: install-systemd
.PHONY: test
.PHONY: uninstall
.PHONY: uninstall-bin
.PHONY: uninstall-systemd
