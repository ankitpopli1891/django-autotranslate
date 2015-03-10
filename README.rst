====================
django-autotranslate
====================
|pypi-version| |pypi-downloads-day| |pypi-downloads-week| |pypi-downloads-month|
    
A simple Django app to autotranslate `.po` files using google translate.

    Disclaimer: This code seems to work fine, and says what it does. 

Caution:
--------

#. The code is highly unoptimized (at least in my opinion).
#. Lacks proper Documentation.
#. Lacks Test Cases.

Installation:
-------------

    $  pip install django-autotranslate
    
Quickstart:
-----------

    **Assumption:** you already have run `makemessages` command and `.po` files have been generated.

#. Add 'autotranslate' to **INSTALLED_APPS** setting.
#. run the following command to see the magic happen (fingers crossed):
   
    $  python manage.py translate_messages
   
.. |pypi-version| image:: https://pypip.in/v/django-autotranslate/badge.png
    :target: https://pypi.python.org/pypi/django-autotranslate/

.. |pypi-downloads-day| image:: https://pypip.in/d/django-autotranslate/badge.png?period=day
    :target: https://pypi.python.org/pypi/django-autotranslate/

.. |pypi-downloads-week| image:: https://pypip.in/d/django-autotranslate/badge.png?period=week
    :target: https://pypi.python.org/pypi/django-autotranslate/

.. |pypi-downloads-month| image:: https://pypip.in/d/django-autotranslate/badge.png?period=month
    :target: https://pypi.python.org/pypi/django-autotranslate/
   
