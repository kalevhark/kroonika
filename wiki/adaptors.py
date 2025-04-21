from inlineedit.adaptors import BasicAdaptor
"Custom adaptors"

class FormattedMarkdownAdaptor(BasicAdaptor):

    def display_value(self):
        "Returns the field value to be shown to users"
        return self._model.__getattribute__('formatted_markdown')

