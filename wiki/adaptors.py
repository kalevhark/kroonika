from inlineedit.adaptors import BasicAdaptor
"Custom adaptors"

class FormattedMarkdownAdaptor(BasicAdaptor):

    def display_value(self):
        return self._model.__getattribute__('formatted_markdown')

