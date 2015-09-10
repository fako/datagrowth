from __future__ import unicode_literals, absolute_import, print_function, division

from core.models.resources.http import BrowserResource


class GoogleTranslate(BrowserResource):

    URI_TEMPLATE = "https://translate.google.nl/#{}/{}/{}"

    def transform(self, soup):
        """

        :return:
        """
        confidences = soup.find_all(class_="gt-baf-cts")
        words = soup.find_all(class_="gt-baf-word-clickable")
        meanings = soup.find_all(class_="gt-baf-translations")
        fallback = next(word for word in soup.find_all(class_="hps") if word.parent["id"] == "result_box")

        def process_info(word, meaning, confidence, fallback):
            if word is not None:
                word = word.text
                meaning = meaning.text
            else:
                word = unicode(fallback)  # TODO: make Python3 variant
                meaning = ""
            if confidence is not None:
                confidence = int(confidence["style"].split(" ")[1][:-3])  # confidence expressed like: "width: 24px;"
            return word, meaning, confidence

        return [
            {
                "language": self.request["args"][1],
                "word": word,
                "meanings": meaning,
                "confidence": confidence
            }
            for word, meaning, confidence in map(process_info, words, meanings, confidences, fallback)
        ]
