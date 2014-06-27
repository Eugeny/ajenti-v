#!/bin/bash
PLUGIN=$1
. $PLUGIN/package.desc

BUILDDIR=build
DISTDIR=dist
PLUGINDIR=/var/lib/ajenti/plugins

SPEC=./$PACKAGE.spec

echo Building package $PACKAGE

rm -rf $BUILDDIR > /dev/null
mkdir $DISTDIR $BUILDDIR 2> /dev/null

ACTUAL_RPM_BUILD_ROOT=$BUILDDIR/BUILDROOT/$PACKAGE-$VERSION-1.x86_64

cat > $SPEC <<END
%define name $PACKAGE
%define version $VERSION
%define unmangled_version $VERSION
%define release 1

Summary: $DESCRIPTION
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{version}.tar.gz
License: AGPLv3
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Eugene Pankov <e@ajenti.org>
Url: http://ajenti.org/

requires: $RPM_DEPENDS
provides: $PROVIDES

%description
$DESCRIPTION

%prep
%setup -n %{name}-%{unmangled_version} -n %{name}-%{unmangled_version}

%build

%install
mkdir ../../../$ACTUAL_RPM_BUILD_ROOT
cp -r var ../../../$ACTUAL_RPM_BUILD_ROOT

%clean
rm -rf ../../../$ACTUAL_RPM_BUILD_ROOT

%files
/var

%post
$POSTINST

END

mkdir -p $BUILDDIR/SOURCES
mkdir -p $BUILDDIR/BUILD

mkdir -p $BUILDDIR/$PACKAGE-$VERSION/$PLUGINDIR
cp -rv $PLUGIN $BUILDDIR/$PACKAGE-$VERSION/$PLUGINDIR

TGZ=$PACKAGE-$VERSION.tar.gz
RPMTOPDIR=`realpath $BUILDDIR`

cd $BUILDDIR && tar czf ../$TGZ $PACKAGE-$VERSION && cd ..
rm -r $BUILDDIR/$PACKAGE-$VERSION
mv $TGZ $BUILDDIR/SOURCES
rpmbuild --define "_topdir $RPMTOPDIR" -ba $SPEC

mv $BUILDDIR/RPMS/*/*.rpm dist/

rm $SPEC