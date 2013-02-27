#!/bin/bash -x

# Enforce some consistency in whitespace - just to avoid spurious whitespaces changes

files=`hg loc '*.py' '*.html' '*.css' '*.rst' '*.txt' '*.js' | egrep -v '/lockfiles.py|LICENSE-MERGELY.html|/codemirror/|/fontello/|(graph|mergely|native.history|select2/select2|yui.flot)\.js$'`
sed -i "s,`printf '\t'`,    ,g" $files
sed -i "s,  *$,,g" $files

sed -i 's,\([^ /]\){,\1 {,g' `hg loc '*.css'`
sed -i 's|^\([^ /].*,\)\([^ ]\)|\1 \2|g' `hg loc '*.css'`

sed -i 's/^\(    [^: ]*\) *: *\([^/]\)/\1: \2/g' kallithea/public/css/{style,contextbar}.css
sed -i '1s|, |,|g' kallithea/public/css/{style,contextbar}.css
sed -i 's/^\([^ ,/]\+ [^,]*[^ ,]\) *, *\(.\)/\1,\n\2/g' kallithea/public/css/{style,contextbar}.css
sed -i 's/^\([^ ,/].*\)   */\1 /g' kallithea/public/css/{style,contextbar}.css
sed -i 's,^--$,-- ,g' kallithea/templates/email_templates/main.txt

hg diff
