#!/bin/bash
PLUGIN=$1
. $PLUGIN/package.desc

BUILDDIR=build
DISTDIR=dist
PLUGINDIR=/var/lib/ajenti/plugins
DEBIANDIR=$BUILDDIR/DEBIAN

echo Building package $PACKAGE

rm -rf $BUILDDIR > /dev/null
mkdir $DISTDIR $BUILDDIR $DEBIANDIR 2> /dev/null

cat > $DEBIANDIR/control <<END
Source: $PACKAGE
Section: admin
Priority: optional
Maintainer: Eugene Pankov <e@ajenti.org>
Package: $PACKAGE
Version: $VERSION
Architecture: all
Homepage: http://ajenti.org/
Depends: $DEB_DEPENDS
Provides: $PROVIDES
Description: $DESCRIPTION

END

echo "#!/bin/bash" > $DEBIANDIR/postinst
echo "$POSTINST" >> $DEBIANDIR/postinst
chmod 755 $DEBIANDIR/postinst

mkdir -p $BUILDDIR/$PLUGINDIR/$PLUGIN
cp -r $PLUGIN/* $BUILDDIR/$PLUGINDIR/$PLUGIN
find $BUILDDIR -name '*.pyc' -delete

dpkg-deb -Z gzip -b $BUILDDIR $DISTDIR/"$PACKAGE"_"$VERSION".deb
