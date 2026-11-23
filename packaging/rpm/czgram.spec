# CzGram for Fedora, RHEL and its rebuilds (Rocky, AlmaLinux), and openSUSE.
# Build from a checkout with packaging/rpm/build_rpm.sh, which passes the checkout as czgram_top.
# The files are installed by packaging/stage.sh, the same script the .deb and Arch packages use.

Name:           czgram
Version:        2.0.0
Release:        1%{?dist}
Summary:        Czech grammar lookup on the PrintScreen key
License:        MIT
URL:            https://github.com/unforged1/CzGram
BuildArch:      noarch

BuildRequires:  python3
%if 0%{?suse_version}
BuildRequires:  python3-Pillow
Requires:       python3 >= 3.9
Requires:       python3-tk
Requires:       python3-Pillow
Requires:       python3-gobject
Requires:       tesseract-ocr
Requires:       tesseract-ocr-traineddata-czech
Requires:       libX11-6
Requires:       xrandr
Requires:       dejavu-fonts
%else
BuildRequires:  python3-pillow
Requires:       python3 >= 3.9
Requires:       python3-tkinter
Requires:       python3-pillow
Requires:       python3-gobject-base
Requires:       tesseract
Requires:       tesseract-langpack-ces
Requires:       libX11
Requires:       xrandr
Requires:       dejavu-sans-fonts
%endif
Recommends:     xdg-desktop-portal
Suggests:       xdg-utils

%description
Press PrintScreen while solving Czech exercises. CzGram finds gaps and
questions on screen, by OCR or from the page's HTML, and shows the matching
grammar rule in a small bar at the top of the screen, optionally explained
by an animated mascot.

%prep
%{!?czgram_top:%{error:czgram_top is not set; build with packaging/rpm/build_rpm.sh}}

%build

%install
sh %{czgram_top}/packaging/stage.sh %{buildroot}
install -Dm644 %{czgram_top}/LICENSE %{buildroot}%{_datadir}/licenses/%{name}/LICENSE
# Compiled here so the package owns the cache files and removes them on uninstall.
python3 -m compileall -q -d /usr/lib/czgram %{buildroot}/usr/lib/czgram

%files
%{_bindir}/czgram
/usr/lib/czgram
%{_datadir}/czgram
%{_datadir}/applications/czgram.desktop
%{_datadir}/icons/hicolor/64x64/apps/czgram.png
%{_datadir}/doc/czgram
%{_datadir}/licenses/%{name}

%changelog
* Mon Nov 23 2026 unforged <unforged.crl@gmail.com> - 2.0.0-1
- First RPM package: bulk mode, offline rules, OCR and page reading as on the other systems
