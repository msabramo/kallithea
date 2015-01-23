Kallithea License
=================

Kallithea as a whole is copyrighted by various authors and is licensed under
the terms of the GNU General Public License, version 3 (GPLv3), which is a
license published by the Free Software Foundation,
Inc. [A copy of GPLv3](/COPYING) is included herein.

Some individual files have copyright notices and those who offer changes to
those files should update the copyright notices in those specific files if
they so chose.

However, the definitive list of copyright holders for this project is kept in
[the about page template](kallithea/templates/about.html) so that it is
displayed appropriately when Kallithea is installed.  This is the most
important place to update copyright notices. 

Third-Party Code Incorporated in Kallithea
==========================================

Various third-party code under GPLv3-compatible licenses is included as part
of Kallithea.



Bootstrap
---------

Kallithea incorporates parts of the Javascript system called
[Bootstrap](http://getbootstrap.com/), which is:

Copyright &copy; 2012 Twitter, Inc.

and licensed under
[the Apache License 2.0](http://www.apache.org/licenses/LICENSE-2.0.html).

A copy of the Apache License 2.0 is also included in this distribution in its
entirety in the file Apache-License-2.0.txt



Codemirror
----------

Kallithea incorporates parts of the Javascript system called
[Codemirror](http://codemirror.net/), version 4.7.0, which is primarily:

Copyright &copy; 2013-2014 by Marijn Haverbeke <marijnh@gmail.com>

and licensed under the MIT-permissive license, which is
[included in this distribution](MIT-Permissive-License.txt).

Additional files from upstream Codemirror are copyrighted by various authors
and licensed under other permissive licenses.  The sub-directories under
[.../public/codemirror](kallithea/public/codemirror) include the copyright and
license notice and information as they appeared in Codemirror's upstream
release.



jQuery
------

Kallithea incorporates the Javascript system called
[jQuery](http://jquery.org/),
[herein](kallithea/public/js/jquery-1.11.1.min.js), and the Corresponding
Source can be found in https://github.com/jquery/jquery at tag 1.11.1
(mirrored at https://kallithea-scm.org/repos/mirror/jquery/files/1.11.1/ ).

It is Copyright 2013 jQuery Foundation and other contributors http://jquery.com/ and is under an
[MIT-permissive license](MIT-Permissive-License.txt).



Mousetrap
---------

Kallithea incorporates parts of the Javascript system called
[Mousetrap](http://craig.is/killing/mice/), which is:

   Copyright 2013 Craig Campbell

and licensed under
[the Apache License 2.0](http://www.apache.org/licenses/LICENSE-2.0.html).

A [copy of the Apache License 2.0](Apache-License-2.0.txt) is also included
in this distribution.



Mergely
-------

Kallithea incorporates some code from the Javascript system called
[Mergely](http://http://www.mergely.com/), version 3.3.9.
[Mergely's license](http://www.mergely.com/license.php), a
[copy of which is included in this repository](LICENSE-MERGELY.html),
is (GPL|LGPL|MPL).  Kallithea as GPLv3'd project chooses the GPL arm of that
tri-license.



Select2
-------

Kallithea incorporates parts of the Javascript system called
[Select2](http://ivaynberg.github.io/select2/), which is:

Copyright 2012 Igor Vaynberg (and probably others)

and is licensed [under the following license](https://github.com/ivaynberg/select2/blob/master/LICENSE):

> This software is licensed under the Apache License, Version 2.0 (the
> "Apache License") or the GNU General Public License version 2 (the "GPL
> License"). You may choose either license to govern your use of this
> software only upon the condition that you accept all of the terms of either
> the Apache License or the GPL License.

A [copy of the Apache License 2.0](Apache-License-2.0.txt) is also included
in this distribution.

Kallithea will take the Apache license fork of the dual license, since
Kallithea is GPLv3'd.



Select2-Bootstrap-CSS
---------------------

Kallithea incorporates some CSS from a system called
[Select2-bootstrap-css](https://github.com/t0m/select2-bootstrap-css), which
is:

Copyright &copy; 2013 Tom Terrace (and likely others)

and licensed under the MIT-permissive license, which is
[included in this distribution](MIT-Permissive-License.txt).



History.js
----------

Kallithea incorporates some CSS from a system called History.js, which is

Copyright 2010-2011 Benjamin Arthur Lupton <contact@balupton.com>

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.



YUI
---

Kallithea incorporates parts of the Javascript system called
[YUI 2 — Yahoo! User Interface Library](http://yui.github.io/yui2/docs/yui_2.9.0_full/),
which is made available under the [BSD License](http://yuilibrary.com/license/):

Copyright &copy; 2013 Yahoo! Inc. All rights reserved.

Redistribution and use of this software in source and binary forms, with or
without modification, are permitted provided that the following conditions are
met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of Yahoo! Inc. nor the names of YUI's contributors may be
  used to endorse or promote products derived from this software without
  specific prior written permission of Yahoo! Inc.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


Kallithea includes a minified version of YUI 2.9. To build yui.2.9.js:

    git clone https://github.com/yui/builder
    git clone https://github.com/yui/yui2
    cd yui2/
    git checkout hudson-yui2-2800
    ln -sf JumpToPageDropDown.js src/paginator/js/JumpToPageDropdown.js # work around inconsistent casing
    rm -f tmp.js
    for m in yahoo event dom connection animation dragdrop element datasource autocomplete container event-delegate json datatable paginator; do
      rm -f build/\$m/\$m.js
      ( cd src/\$m && ant build deploybuild ) && sed -e 's,@VERSION@,2.9.0,g' -e 's,@BUILD@,2800,g' build/\$m/\$m.js >> tmp.js
    done
    java -jar ../builder/componentbuild/lib/yuicompressor/yuicompressor-2.4.4.jar tmp.js -o yui.2.9.js

In compliance with GPLv3 the Corresponding Source for this Object Code is made
available on
[https://kallithea-scm.org/repos/mirror](https://kallithea-scm.org/repos/mirror).



Flot
----

Kallithea incorporates some CSS from a system called
[Flot](http://code.google.com/p/flot/), which is:

Copyright 2006 Google Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

A [copy of the Apache License 2.0](Apache-License-2.0.txt) is also included
in this distribution.



Migrate
-------

Kallithea incorporates in kallithea/lib/dbmigrate/migrate parts of the Python
system called [Migrate or sqlalchemy-migrate](https://github.com/stackforge/sqlalchemy-migrate),
which is:

Copyright (c) 2009 Evan Rosson, Jan Dittberner, Domen Kožar

and licensed under the MIT-permissive license, which is
[included in this distribution](MIT-Permissive-License.txt).


Icon fonts
----------

Kallithea incorporates subsets of both
[Font Awesome](http://fontawesome.io) and
[GitHub Octicons](https://octicons.github.com) for icons. Font Awesome is:

Copyright (c) 2012, Dave Gandy

Octicons is:

Copyright (c) 2012-2014 GitHub

These two sets are distributed under [SIL OFL 1.1](http://scripts.sil.org/OFL)
and have been combined into one font called "kallithea."


EOF
