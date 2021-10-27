DESTDIR ?= /
moduledir ?= $(DESTDIR)/usr/share/mender/modules/v3
inventorydir ?= $(DESTDIR)/usr/share/mender/inventory
scriptdir ?= $(DESTDIR)/usr/lib/mender-configure/apply-device-config.d

# No-op for this project
build:

# "check" is standard is autotools projects, make an alias.
check: test

test:
	$(MAKE) -C tests/unit test

install: install-bin install-systemd

install-bin:
	install -d -m 755 $(scriptdir)
	install -d -m 755 $(moduledir)
	install -m 755 src/mender-configure $(moduledir)/

	install -d -m 755 $(inventorydir)
	install -m 755 src/mender-inventory-mender-configure $(inventorydir)/

install-demo:
	install -d -m 755 $(scriptdir)
	install -m 755 demo/mender-demo-raspberrypi-led $(scriptdir)/

install-scripts:
	install -d -m 755 $(scriptdir)
	install -m 755 scripts/timezone $(scriptdir)/

install-systemd:
	install -d -m 755 $(DESTDIR)/lib/systemd/system
	install -m 644 support/mender-configure-apply-device-config.service $(DESTDIR)/lib/systemd/system/

uninstall: uninstall-bin uninstall-systemd

uninstall-bin:
	rm -f $(moduledir)/mender-configure
	rmdir -p --ignore-fail-on-non-empty $(moduledir)

	rm -f $(inventorydir)/mender-inventory-mender-configure
	rmdir -p --ignore-fail-on-non-empty $(inventorydir)

uninstall-demo:
	rm -f $(scriptdir)/mender-demo-raspberrypi-led
	rmdir -p --ignore-fail-on-non-empty $(scriptdir)

uninstall-scripts:
	rm -f $(scriptdir)/timezone
	rmdir -p --ignore-fail-on-non-empty $(scriptdir)

uninstall-systemd:
	rm -f $(DESTDIR)/lib/systemd/system/mender-configure-apply-device-config.service
	rmdir -p --ignore-fail-on-non-empty $(DESTDIR)/lib/systemd/system

.PHONY: build
.PHONY: check
.PHONY: install
.PHONY: install-bin
.PHONY: install-demo
.PHONY: install-scripts
.PHONY: install-systemd
.PHONY: test
.PHONY: uninstall
.PHONY: uninstall-bin
.PHONY: uninstall-demo
.PHONY: uninstall-scripts
.PHONY: uninstall-systemd
