from HIF.input.http.core import JsonQueryLink
from HIF.exceptions import HIFHttpError40X, HIFHttpLinkPending


class GoogleLink(JsonQueryLink):

    HIF_query_parameter = 'q'
    HIF_namespace = "google"

    def enable_auth(self):
        super(GoogleLink, self).enable_auth()
        key = self.config.key
        self._link += unicode(('&key={}'.format(key)))

    def handle_error(self):
        try:
            return super(GoogleLink, self).handle_error()
        except HIFHttpError40X, exception:
            if self.status == 403:
                raise HIFHttpLinkPending(exception.message)
            else:
                raise exception

    class Meta:
        proxy = True


class GoogleImage(GoogleLink):

    # HIF interface
    HIF_link = 'https://www.googleapis.com/customsearch/v1'
    HIF_parameters = {
        'searchType':'image',
    }
    HIF_objective = {
        "link": None,
        "image.width": None,
        "image.height": None,
        "image.thumbnailLink": None
    }
    HIF_translations = {
        "image.width": "width",
        "image.height": "height",
        "image.thumbnailLink": "thumbnailLink"
    }

    def enable_auth(self):
        super(GoogleImage, self).enable_auth()
        cx = self.config.cx
        self._link += unicode(('&cx={}'.format(cx)))

    class Meta:
        app_label = "HIF"
        proxy = True


class YouTubeSearch(GoogleLink):

    # HIF interface
    HIF_link = 'https://www.googleapis.com/youtube/v3/search'
    HIF_parameters = {
        'type':'video',
        'part':'id,snippet'
    }
    HIF_objective = {
        "id.videoId": None,
        "snippet.thumbnails.medium.url": None
    }
    HIF_translations = {
        "id.videoId": "vid",
        "snippet.thumbnails.medium.url": "thumbnail"
    }

    class Meta:
        app_label = "HIF"
        proxy = True