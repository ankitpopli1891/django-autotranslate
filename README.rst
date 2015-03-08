====================
django-autotranslate
====================

A simple Django app to autotranslate `.po` files using google translate.

    Disclaimer: This code seems to work fine, and says what it does. 

Caution:
--------

#. The code is highly unoptimized (at least in my opinion).
#. Lacks proper Documentation.
#. Lacks Test Cases.

Installation:
-------------

    pip install django-autotranslate
    
Quickstart:
-----------

    Assumption: you already have run `makemessages` command and `.po` files have been generated.

#. Add 'autotranslate' to **INSTALLED_APPS** setting.
#. run the following command to see the magic happen (fingers crossed):
   
   python manage.py translate_messages