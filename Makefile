DESTDIR ?= /
prefix ?= $(DESTDIR)
moduledir ?= /usr/share/mender/modules/v3
inventorydir ?= /usr/share/mender/inventory
scriptdir ?= /usr/lib/mender-configure/apply-device-config.d
systemd_unitdir ?= /lib/systemd

# No-op for this project
build:

# "check" is standard is autotools projects, make an alias.
check: test

test:
	$(MAKE) -C tests/unit test

install: install-bin install-systemd

install-bin:
	install -d -m 755 $(prefix)$(scriptdir)
	install -d -m 755 $(prefix)$(moduledir)
	install -m 755 src/mender-configure $(prefix)$(moduledir)/

	install -d -m 755 $(prefix)$(inventorydir)
	install -m 755 src/mender-inventory-mender-configure $(prefix)$(inventorydir)/

install-demo:
	install -d -m 755 $(prefix)$(scriptdir)
	install -m 755 demo/mender-demo-raspberrypi-led $(prefix)$(scriptdir)/

install-scripts:
	install -d -m 755 $(prefix)$(scriptdir)
	install -m 755 scripts/timezone $(prefix)$(scriptdir)/

install-systemd:
	install -m 755 -d $(prefix)$(systemd_unitdir)/system
	install -m 644 support/mender-configure-apply-device-config.service $(prefix)$(systemd_unitdir)/system/

uninstall: uninstall-bin uninstall-systemd

uninstall-bin:
	rm -f $(prefix)$(moduledir)/mender-configure
	rmdir -p --ignore-fail-on-non-empty $(prefix)$(moduledir)

	rm -f $(prefix)$(inventorydir)/mender-inventory-mender-configure
	rmdir -p --ignore-fail-on-non-empty $(prefix)$(inventorydir)

uninstall-demo:
	rm -f $(prefix)$(scriptdir)/mender-demo-raspberrypi-led
	rmdir -p --ignore-fail-on-non-empty $(prefix)$(scriptdir)

uninstall-scripts:
	rm -f $(prefix)$(scriptdir)/timezone
	rmdir -p --ignore-fail-on-non-empty $(prefix)$(scriptdir)

uninstall-systemd:
	rm -f $(prefix)$(systemd_unitdir)/system/mender-configure-apply-device-config.service
	rmdir -p --ignore-fail-on-non-empty $(prefix)$(systemd_unitdir)/system

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
