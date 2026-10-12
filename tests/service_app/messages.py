from django.utils.translation import gettext as _
from django.utils.translation import ngettext


def messages(name, count):
    return [
        # plain text with punctuation that must not come back HTML escaped
        _("Good morning! Fish & chips are 'ready'."),
        # printf style named placeholder
        _("Hello %(name)s, welcome back.") % {"name": name},
        # positional placeholder
        _("Saved %s") % name,
        # brace style placeholder
        _("You have {count} new messages.").format(count=count),
        # plural forms
        ngettext(
            "%(count)d file was translated.", "%(count)d files were translated.", count
        )
        % {"count": count},
        # markup and a placeholder in an attribute
        _('Read the <a href="%(url)s">documentation</a> first.') % {"url": "/docs"},
    ]
