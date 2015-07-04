from __future__ import unicode_literals, absolute_import, print_function, division
from django.utils.encoding import python_2_unicode_compatible

from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey, ContentType

from jsonfield import JSONField


class OrganismIterator(object):

    def __init__(self, content):
        self._content = content
        self._index = 0
        self._candidate = None

    def __iter__(self):
        return self

    def next(self):
        if self._candidate is None:
            try:
                self._candidate = self._content[self._index]
            except IndexError:
                raise StopIteration()
        result = None
        try:
            if isinstance(self._candidate, dict):
                result = self._candidate
                self._candidate = None
            elif isinstance(self._candidate, list):
                result = next(self._candidate)
        except StopIteration:
            self._candidate = None
            return self.next()
        return result


@python_2_unicode_compatible
class Organism(models.Model):

    community = GenericForeignKey(ct_field="community_type", fk_field="community_id")
    community_type = models.ForeignKey(ContentType, related_name="+")
    community_id = models.PositiveIntegerField()

    schema = JSONField(default=None, null=False, blank=False)  # BUG: schema does not throw IntegrityError on None

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    @staticmethod
    def validate(data, schema):
        raise NotImplementedError()

    def update(self, data, validate=True):
        raise NotImplementedError()

    @property
    def content(self):
        raise NotImplementedError()

    def output(self, *args):
        raise NotImplementedError()

    @property
    def url(self):  # TODO: implement?
        """
        TODO: Uses Django reverse

        :return:
        """
        if not self.id:
            raise ValueError("Can't get path for unsaved Collective")
        return "ind|col/{}/".format(self.id)

    def __str__(self):
        return "{} {}".format(self.__class__.__name__, self.id)

    class Meta:
        abstract = True