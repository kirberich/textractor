import re
import six
from collections import OrderedDict

from bs4 import BeautifulSoup
from bs4.element import NavigableString, CData

BLOCK_TAGS = ['p', 'div', 'body', 'td', 'article', 'main', 'section', 'h1', 'h2', 'h3', 'li']


class ElementFilter(object):
    """ A filter defining a search in a BeautifulSoup object """
    def __init__(self, tag_name=None, attrs=None):
        self.tag_name = tag_name
        self.attrs = attrs

    def find_in_soup(self, soup):
        return soup.findAll(self.tag_name, attrs=self.attrs or {})

    @classmethod
    def find_many_in_soup(cls, soup, filters):
        results = set([])
        for f in filters:
            results = results | set(f.find_in_soup(soup))
        return list(results)


def remove_whitespace(text):
    """ Collapses duplicated spaces, tabs and line-breaks, strips the result. """
    text = re.sub('\n+', '\n', text)

    # Get rid of duplicate spaces
    text = re.sub(r' +', ' ', text)

    text = re.sub(r"\t+", "\t", text)
    return six.text_type(text).strip()


def extract(html, element_filters=None, remove_elements=None, element_groupers=None, join_texts=False, join_texts_with="\n"):
    """ Extracts texts from html. It returns a OrderedDict of elements (by default just body) and a list of texts in block elements:
        {
            'body':[
                'Some text in a block element',
                'More text in another block element'
            ],
            '.some-class': [
                'Headline',
                'List element'
                'Other list element'
            ]
        }

        The following arguments all take lists of ElementFilters:
            element_filters defines which bits of html to parse. Defaults to the body tag.
            remove_elements defines elements to be removed completely. Script tags are always removed.
            element_groupers defines groups of elements. Anything outside these groups will not be returned.

        Set join_texts to true to join together all strings inside one element group
        join_texts_with defines how strings should be joined together (defaults to \n)

    """
    # DIRTY HACK
    # BeautifulSoup does a completely useless check on short markup to see if it's actually a filename, to protect against "beginner problems"
    # This fails on appengine if the markup contains unicode. So we pad the string to avoid that check.
    html = html.ljust(257)
    soup = BeautifulSoup(html, 'lxml')

    # Remove script tags and anything else specified in remove_elements
    remove_elements = (remove_elements or []) + [ElementFilter(tag_name='script')]
    [s.extract() for s in ElementFilter.find_many_in_soup(soup, remove_elements)]

    # If specific elements in the html were specified in element_filters, use those. Fall back to using the whole body
    element_filters = element_filters or [ElementFilter(tag_name='body')]
    elements = ElementFilter.find_many_in_soup(soup, element_filters)

    # Set up grouping defined by element_groupers, fall back to using 'elements'
    element_groups = OrderedDict()
    if element_groupers:
        for grouper in element_groupers:
            for result in grouper.find_in_soup(soup):
                element_groups[result] = []
    else:
        element_groups = OrderedDict([(element, []) for element in elements])

    for element in elements:
        last_block_element = element
        last_group_element = None

        for current in [element] + list(element.descendants):

            # Remember last seen block/grouping element and remember if a new block was started
            if current.name in BLOCK_TAGS:
                last_block_element = current
                new_block = True
                if current in element_groups:
                    last_group_element = current

            # Bail here if the current node doesn't contain a string
            if type(current) not in (NavigableString, CData) or not current.string:
                continue

            # Find closest block tag, append current string to last one if both are inside the same block element
            append = False
            for ancestor in current.parents:
                if ancestor.name in BLOCK_TAGS and ancestor == last_block_element:
                    append = True
                    break

            if last_group_element and last_group_element in current.parents:
                current_group = element_groups.setdefault(last_group_element, [])
                if append and current_group and not new_block:
                    current_group[-1] += current.string
                else:
                    current_group.append(current.string)
                    new_block = False
                element_groups[last_group_element] = current_group

    for group in element_groups:
        if join_texts:
            stripped_texts = remove_whitespace(join_texts_with.join(element_groups[group]))
        else:
            stripped_texts = [remove_whitespace(text) for text in element_groups[group]]

        element_groups[group] = stripped_texts

    return element_groups
