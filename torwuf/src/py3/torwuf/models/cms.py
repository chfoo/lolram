'''CMS database keys'''


class ArticleCollection(object):
    COLLECTION = 'cms_articles'
    PUBLICATION_DATE = 'date'
    UPDATED_DATE = 'updated'
    TAGS = 'tags'
    RELATED_TAGS = 'related_tags'
    TITLE = 'title'
    UUID = 'uuid'
    TEXT = 'text'
    FILENAME = 'filename'
    FILE_SHA1 = 'sha1'
    PRIVATE = 'private'
    LEGACY_ALLOW_RAW_HTML = 'allow_raw_html'


class TagCollection(object):
    COLLECTION = 'cms_tags'
    TITLE = 'title'
    COUNT = 'count'


class TagCountCollection(object):
    COLLECTION = 'cms_tag_counts'
    COUNT = 'value'


class CommentCollection(object):
    COLLECTION = 'cms_comments'
    PUBLICATION_DATE = 'date'
    UPDATED_DATE = 'updated'
    TEXT = 'text'
    ACCOUNT_ID = 'account_id'
    LEGACY_BLOGGER_ID = 'blogger_id'
    LEGACY_ALLOW_RAW_HTML = 'allow_raw_html'
    ARTICLE_ID = 'article_id'


class LegacyBlogLookupCollection(object):
    COLLECTION = 'cms_legacy_blog_lookup'
    ARTICLE_ID = 'article_id'
