#!/bin/bash
PLUGIN=$1
. $PLUGIN/package.desc

BUILDDIR=build
DISTDIR=dist
PLUGINDIR=/var/lib/ajenti/plugins
DEBIANDIR=$BUILDDIR/DEBIAN

echo Building package $PACKAGE

rm -rf $BUILDDIR
mkdir $DISTDIR $BUILDDIR $DEBIANDIR

cat > $DEBIANDIR/control <<END
Source: $PACKAGE
Section: admin
Priority: optional
Maintainer: Eugene Pankov <e@ajenti.org>
Package: $PACKAGE
Version: $VERSION
Architecture: all
Homepage: http://ajenti.org/
Depends: $DEPENDS
Provides: $PROVIDES
Description: $DESCRIPTION

END

echo "$POSTINST" > $DEBIANDIR/postinst
chmod 755 $DEBIANDIR/postinst

mkdir -p $BUILDDIR/$PLUGINDIR/$PLUGIN
cp -rv $PLUGIN/* $BUILDDIR/$PLUGINDIR/$PLUGIN
find $BUILDDIR -name '*.pyc' -delete

dpkg-deb -b $BUILDDIR $DISTDIR/"$PACKAGE"_"$VERSION".deb
