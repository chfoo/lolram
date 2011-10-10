# coding: utf-8
"""
    `sqlamp` --- Materialized Path for SQLAlchemy
    =============================================

    :author: `Anton Gritsay <anton@angri.ru>`_, http://angri.ru
    :version: %(version)s
    :license: 2-clause BSD (see LICENSE)
    :download: http://sqlamp.angri.ru/sqlamp-%(version)s.tar.gz

    :mod:`sqlamp` is an implementation of an efficient algorithm for working
    with hierarchical data structures --- `Materialized Path`. :mod:`sqlamp`
    uses (and depends of) `SQLAlchemy <http://sqlalchemy.org>`_.

    `Materialized Path` is a way to store (and fetch) a trees in a relational
    databases. It is the compromise between `Nested Sets` and `Adjacency
    Relations` in respect to simplicity and efficiency. Method was promoted
    by `Vadim Tropashko`_ in his book `SQL Design Patterns`_. Vadim's
    description of the method can be read in his article `Trees in SQL:
    Nested Sets and Materialized Path (by Vadim Tropashko)`_.

    Implemented features:

        * Setting up with ``declarative.ext`` or without it.
        * Saving node roots --- if no parent set for node. The tree will have
          a new `tree_id`.
        * Saving child nodes --- if node has some parent. The whole dirty job
          of setting values in `tree_id`, `path` and `depth` fields is done
          by `sqlamp`.
        * Fetching node's descendants, ancestors and children using the most
          efficient way available (see :class:`MPInstanceManager`)
        * Autochecking exhaustion of tree size limits --- maximum number of
          children and maximum nesting level (see :class:`MPManager` to learn
          more about limits fine-tuning) is done during session flush.
        * Rebuilding all trees (see :meth:`MPClassManager.rebuild_all_trees`)
          and any subtree (:meth:`MPClassManager.rebuild_subtree`) on the
          basis of Adjacency Relations.
        * Collapsing flat tree returned from query to recursive structure (see
          :func:`tree_recursive_iterator`).
        * Node classes may use `polymorphic inheritance
          <http://www.sqlalchemy.org/docs/05/mappers.html
          #mapping-class-inheritance-hierarchies>`_.

    Moving of nodes is not yet implemented.

    Known-to-work supported DBMS include `sqlite`_ (tested with 3.6.14),
    `MySQL`_ (tested using both MyISAM and InnoDB with server version 5.1.34)
    and `PostgreSQL`_ (tested with 8.3.7), but sqlamp should work with any
    other DBMS supported by SQLAlchemy.

    .. _`Vadim Tropashko`: http://vadimtropashko.wordpress.com
    .. _`Sql Design Patterns`:
       http://www.rampant-books.com/book_2006_1_sql_coding_styles.htm
    .. _`Trees in SQL: Nested Sets and Materialized Path (by Vadim Tropashko)`:
       http://www.dbazine.com/oracle/or-articles/tropashko4
    .. _`sqlite`: http://sqlite.org
    .. _`MySQL`: http://mysql.com
    .. _`PostgreSQL`: http://postgresql.org
"""
import weakref
from operator import attrgetter
import sqlalchemy, sqlalchemy.orm, sqlalchemy.orm.exc
from sqlalchemy.orm.mapper import class_mapper
from sqlalchemy.ext.declarative import DeclarativeMeta as BaseDeclarativeMeta


__all__ = [
    'MPManager', 'tree_recursive_iterator', 'DeclarativeMeta',
    'PathOverflowError', 'TooManyChildrenError', 'PathTooDeepError'
]

__version__ = (0, 5, 2)
__doc__ %= {'version': '.'.join(map(str, __version__))}


ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
PATH_FIELD_LENGTH = 255


class PathOverflowError(Exception):
    "Base class for exceptions in calculations of node's path."

class TooManyChildrenError(PathOverflowError):
    "Maximum children limit is exceeded. Raised during flush."

class PathTooDeepError(PathOverflowError):
    "Maximum depth of nesting limit is exceeded. Raised during flush."


def inc_path(path, steplen):
    """
    Simple arithmetical operation --- incrementation of an integer number
    (with radix of `len(ALPHABET)`) represented as string.

    :param path:
        `str`, the path to increment.
    :param steplen:
        `int`, the number of maximum characters to carry overflow.
    :returns:
        new path which is greater than `path` by one.
    :raises PathOverflowError:
        when incrementation of `path` cause to carry overflow by number
        of characters greater than `steplen`.

    >>> inc_path('0000', 4)
    '0001'
    >>> inc_path('3GZU', 4)
    '3GZV'
    >>> inc_path('337Z', 2)
    '3380'
    >>> inc_path('GWZZZ', 5)
    'GX000'
    >>> inc_path('ABZZ', 2)
    Traceback (most recent call last):
        ...
    PathOverflowError
    """
    parent_path, path = path[:-steplen], path[-steplen:]
    path = path.rstrip(ALPHABET[-1])
    if not path:
        raise PathOverflowError()
    zeros = steplen - len(path)
    path = path[:-1] + \
           ALPHABET[ALPHABET.index(path[-1]) + 1] + \
           ALPHABET[0] * zeros
    return parent_path + path


class MPOptions(object):
    """
    A container for options for one tree.

    :parameters: see :class:`MPManager`.
    """
    def __init__(self,
                 table,
                 parent_id_field=None,
                 path_field='mp_path',
                 depth_field='mp_depth',
                 tree_id_field='mp_tree_id',
                 steplen=3):

        self.table = table

        self.steplen = steplen

        self.max_children = len(ALPHABET) ** steplen
        self.max_depth = (PATH_FIELD_LENGTH / steplen) + 1

        assert len(table.primary_key.columns) == 1, \
               "Composite primary keys not supported"
        [self.pk_field] = table.primary_key.columns

        if parent_id_field is None:
            self.parent_id_field = table.join(table).onclause.right
        elif isinstance(parent_id_field, basestring):
            self.parent_id_field = table.columns[parent_id_field]
        else:
            assert isinstance(parent_id_field, sqlalchemy.Column)
            assert parent_id_field.table is table
            self.parent_id_field = parent_id_field

        def _check_field(name, field, type_):
            # Check field argument (one of `path_field`, `depth_field` and
            # `tree_id_field`), convert it from field name to `Column` object
            # if needed, create the column object if needed and check the
            # existing `Column` object for sane.
            assert field
            if not isinstance(field, basestring):
                assert isinstance(field, sqlalchemy.Column)
                assert field.table is table
            elif field in table.columns:
                field = table.columns[field]
            else:
                field = sqlalchemy.Column(field, type_(), nullable=False)
                table.append_column(field)
                return field
            assert isinstance(field.type, type_), \
                   "The type of %s field should be %r" % (name, type_)
            assert not field.nullable, \
                   "The %s field should not be nullable" % name
            return field

        self.path_field = _check_field('path', path_field, PathField)
        self.depth_field = _check_field('depth', depth_field, DepthField)
        self.tree_id_field = _check_field('tree_id', tree_id_field, TreeIdField)
        self.fields = (self.path_field, self.depth_field, self.tree_id_field)

        self.indices = [
            sqlalchemy.Index(
                '__'.join((table.name, self.tree_id_field.name,
                           self.path_field.name)),
                self.tree_id_field,
                self.path_field,
                unique=True
            ),
        ]
        map(table.append_constraint, self.indices)

    def order_by_clause(self):
        """
        Get an object applicable for usage as an argument for
        `Query.order_by()`. Used to sort subtree query
        by `tree_id` and `path`.
        """
        return sqlalchemy.sql.expression.ClauseList(
            self.tree_id_field,
            self.path_field
        )


class _InsertionsParamsSelector(object):
    """
    Instances of this class used as values for :class:`TreeIdField`,
    :class:`PathField` and :class:`DepthField` when tree nodes are
    created. It makes a "lazy" query to determine actual values for
    this fields.

    :param opts: instance of :class:`MPOptions`.
    :param session: session which will be used for query.
    :param parent_id: parent's node primary key, may be `None`.
    """
    def __init__(self, opts, session, parent_id):
        self._mp_opts = opts
        self.parent_id = parent_id
        self.session = session
        self._query_result = None

    def _perform_query(self):
        """
        Make a query, get an actual values for `path`, `tree_id`
        and `depth` fields and put them in dict `self._query_result`.
        """
        opts = self._mp_opts
        if self.parent_id is None:
            # a new instance will be a root node.
            # `tree_id` is next unused integer value,
            # `depth` for root nodes is equal to zero,
            # `path` should be empty string.
            query = self.session.execute(sqlalchemy.select([
                (sqlalchemy.func.coalesce(
                    sqlalchemy.func.max(opts.tree_id_field), 0)
                 + 1).label('tree_id')
            ])).fetchone()
            self._query_result = dict(
                path='', depth=0, tree_id=query['tree_id']
            )
        else:
            # a new instance has at least one ancestor.
            # `tree_id` can be used from parent's value,
            # `depth` is parent's depth plus one,
            # `path` will be calculated from two values -
            # the path of the parent node itself and it's
            # last child's path.
            query = self.session.execute(sqlalchemy.select(
                [
                    opts.tree_id_field.label('tree_id'),
                    (opts.depth_field + 1).label('depth'),
                    opts.path_field.label('parent_path'),
                    sqlalchemy.select(
                        [sqlalchemy.func.max(opts.path_field)],
                        opts.parent_id_field == self.parent_id
                    ).label('last_child_path'),
                ],
                opts.pk_field == self.parent_id
            )).fetchone()
            steplen = self._mp_opts.steplen
            if not query['last_child_path']:
                # node is the first child.
                path = query['parent_path'] + ALPHABET[0] * steplen
            else:
                try:
                    path = inc_path(query['last_child_path'], steplen)
                except PathOverflowError:
                    # transform exception `PathOverflowError`, raised by
                    # `inc_path()` to more convenient `TooManyChildrenError`.
                    raise TooManyChildrenError()
            if len(path) > PATH_FIELD_LENGTH:
                raise PathTooDeepError()
            self._query_result = dict(
                path=path, depth=query['depth'], tree_id=query['tree_id']
            )

    @property
    def query_result(self):
        """
        Get query result dict, calling `self._perform_query()`
        for the first time.
        """
        if self._query_result is None:
            self._perform_query()
        return self._query_result


class TreeIdField(sqlalchemy.types.TypeDecorator):
    "Integer field subtype representing node's tree identifier."
    impl = sqlalchemy.Integer
    def process_bind_param(self, value, dialect):
        if not isinstance(value, _InsertionsParamsSelector):
            return value
        return value.query_result['tree_id']

class DepthField(sqlalchemy.types.TypeDecorator):
    "Integer field subtype representing node's depth level."
    impl = sqlalchemy.Integer
    def process_bind_param(self, value, dialect):
        if not isinstance(value, _InsertionsParamsSelector):
            return value
        return value.query_result['depth']

class PathField(sqlalchemy.types.TypeDecorator):
    "Varchar field subtype representing node's path."
    impl = sqlalchemy.String
    def __init__(self):
        super(PathField, self).__init__(PATH_FIELD_LENGTH)
    def process_bind_param(self, value, dialect):
        if not isinstance(value, _InsertionsParamsSelector):
            return value
        return value.query_result['path']
    def adapt_operator(self, op):
        # required for concatenation to work right
        return self.impl.adapt_operator(op)


class MPMapperExtension(sqlalchemy.orm.interfaces.MapperExtension):
    """
    An extension to node class' mapper.

    :param opts: instance of :class:`MPOptions`
    """
    def __init__(self, opts):
        super(MPMapperExtension, self).__init__()
        self._mp_opts = opts

    def before_insert(self, mapper, connection, instance):
        """
        Creates an :class:`_InsertionsParamsSelector` instance and
        sets values of tree_id, depth and path fields to it.
        """
        opts = self._mp_opts
        parent = getattr(instance, opts.parent_id_field.name)
        tree_id = depth = path = _InsertionsParamsSelector(
            opts, sqlalchemy.orm.session.object_session(instance), parent
        )
        setattr(instance, opts.tree_id_field.name, tree_id)
        setattr(instance, opts.path_field.name, path)
        setattr(instance, opts.depth_field.name, depth)

    def after_insert(self, mapper, connection, instance):
        """
        Replaces :class:`_InsertionsParamsSelector` instance (which
        is remains after flush) with actual values of tree_id, depth
        and path fields.
        """
        opts = self._mp_opts
        params_selector = getattr(instance, opts.path_field.name)
        assert isinstance(params_selector, _InsertionsParamsSelector)
        query_result = params_selector.query_result
        setattr(instance, opts.tree_id_field.name, query_result['tree_id'])
        setattr(instance, opts.path_field.name, query_result['path'])
        setattr(instance, opts.depth_field.name, query_result['depth'])


class MPClassManager(object):
    """
    Node class manager. No need to create it by hand: it created
    by :class:`MPManager`.

    :param node_class: class which was mapped to tree table.
    :param opts: instance of :class:`MPOptions`
    """
    def __init__(self, node_class, opts):
        self._mp_opts = opts
        self.node_class = node_class

    @property
    def max_children(self):
        "The maximum number of children in each node, readonly."
        return self._mp_opts.max_children
    @property
    def max_depth(self):
        "The maximum level of nesting in this tree, readonly."
        return self._mp_opts.max_depth

    def __clause_element__(self):
        """
        Allows to use instances of `MPClassManager` directly
        as argument for `sqlalchemy.orm.Query.order_by()`.
        Sort query by `tree_id` and `path` fields. Can be
        used like this (assume that :class:`MPManager` is
        attached to class `Node` and named `'mp'`)::

            query = session.query(Node).filter(root.filter_children())
            query.order_by(Node.mp)

        .. note:: There is no need to sort queries returned by
            :class:`MPInstanceManager`'s `query_*()` methods this way
            as they returned already sorted.
        """
        return self._mp_opts.order_by_clause()

    def rebuild_subtree(self, root_node_id, order_by=None):
        """
        Reset paths for all nodes in subtree defined by `root_node_id`
        on the basis of adjacency relations.

        :param root_node_id:
            the value of subtree root's primary key.
        :param order_by:
            an "order by clause" for sorting children nodes
            in each subtree.
        """
        opts = self._mp_opts
        path, depth, tree_id = sqlalchemy.select(
            [opts.path_field, opts.depth_field, opts.tree_id_field],
            opts.pk_field == root_node_id
        ).execute().fetchone()
        if order_by is None:
            order_by = opts.pk_field
        self._do_rebuild_subtree(
            root_node_id, path, depth, tree_id, order_by
        )

    def _do_rebuild_subtree(self, root_node_id, root_path, root_depth, \
                            tree_id, order_by):
        """
        The main recursive function for rebuilding trees.

        :param root_node_id:
            subtree's root node primary key value.
        :param root_path:
            the pre-calculated path of root node.
        :param root_depth:
            the pre-calculated root node's depth.
        :param tree_id:
            the pre-calculated identifier for this tree.
        :param order_by:
            the children sort order.
        """
        opts = self._mp_opts
        path = root_path + ALPHABET[0] * opts.steplen
        depth = root_depth + 1
        children = sqlalchemy.select(
            [opts.pk_field],
            opts.parent_id_field == root_node_id
        ).order_by(order_by)
        query = opts.table.update()
        for child in children.execute().fetchall():
            [child] = child
            query.where(opts.pk_field == child) \
                 .values({opts.path_field: path, \
                          opts.depth_field: depth, \
                          opts.tree_id_field: tree_id}).execute()
            self._do_rebuild_subtree(child, path, depth, tree_id, order_by)
            path = inc_path(path, opts.steplen)

    def rebuild_all_trees(self, order_by=None):
        """
        Perform a complete rebuild of all trees on the basis
        of adjacency relations.

        Drops indexes before processing and recreates it after.

        :param order_by:
            an "order by clause" for sorting root nodes and a
            children nodes in each subtree.
        """
        opts = self._mp_opts
        order_by = order_by or opts.pk_field
        for index in opts.indices:
            index.drop()
        roots = sqlalchemy.select(
            [opts.pk_field], opts.parent_id_field == None
        ).order_by(order_by)
        update_query = opts.table.update()
        for tree_id, root_node in enumerate(roots.execute().fetchall()):
            [node_id] = root_node
            # resetting path, depth and tree_id for root node:
            update_query.where(opts.pk_field == node_id) \
                        .values({opts.tree_id_field: tree_id + 1,
                                 opts.path_field: '',
                                 opts.depth_field: 0}) \
                        .execute()
            self._do_rebuild_subtree(node_id, '', 0, tree_id + 1, order_by)
        for index in opts.indices:
            index.create()

    def query_all_trees(self, session):
        """
        Query all stored trees.

        :param session: a sqlalchemy `Session` object to bind a query.
        :returns:
            `Query` object with all nodes of all trees sorted as usual
            by `(tree_id, path)`.
        """
        query = sqlalchemy.orm.Query(self.node_class, session=session) \
                              .order_by(self)
        return query


class MPInstanceManager(object):
    """
    A node instance manager, unique for each node. First created
    on access to :class:`MPManager` descriptor from instance.
    Implements API to query nodes related somehow to particular
    node: descendants, ancestors, etc.

    :param opts:
        instance of `MPOptions`.
    :param root_node_class:
        the root class in the node class' polymorphic inheritance hierarchy.
        This class will be used to perform queries.
    :param obj:
        particular node instance.
    """
    __slots__ = ('_mp_opts', '_obj_ref', '_root_node_class')

    def __init__(self, opts, root_node_class, obj):
        self._root_node_class = root_node_class
        self._mp_opts = opts
        self._obj_ref = weakref.ref(obj)

    def _get_obj(self):
        "Dereference weakref and return node instance."
        return self._obj_ref()

    def _get_query(self, obj, session):
        """
        Get a query for the node's class.

        If :attr:`session` is `None` tries to use :attr:`obj`'s session,
        if it is available.

        :param session: a sqlalchemy `Session` object or `None`.
        :return: an object `sqlalchemy.orm.Query`.
        :raises AssertionError:
            if :attr:`session` is `None` and node is not bound
            to a session.
        """
        obj_session = self._get_session_and_assert_flushed(obj)
        if session is None:
            # use node's session only if particular session
            # was not specified
            session = obj_session
        return sqlalchemy.orm.Query(self._root_node_class, session=session)

    def _get_session_and_assert_flushed(self, obj):
        """
        Ensure that node has "real" values in its `path`, `tree_id`
        and `depth` fields and return node's session.

        Determines object session, flushs it if instance is in "pending"
        state and session has `autoflush == True`. Flushing is needed
        for instance's `path`, `tree_id` and `depth` fields hold real
        values applicable for queries. If the node is not bound to a
        session tries to check that it was "persistent" once upon a time.

        :return: session object or `None` if node is in "detached" state.
        :raises AssertionError:
            if instance is in "pending" state and session has `autoflush`
            disabled.
        :raises AssertionError:
            if instance is in "transient" state (has no "persistent" copy
            and is not bound to a session).
        """
        session = sqlalchemy.orm.session.object_session(obj)
        if session is not None:
            if obj in session.new:
                assert session.autoflush, \
                        "instance %r is in 'pending' state and attached " \
                        "to non-autoflush session. call `session.flush()` " \
                        "to be able to get filters and perform queries." % obj
                session.flush()
        else:
            assert all(getattr(obj, field.name) is not None \
                       for field in self._mp_opts.fields), \
                    "instance %r seems to be in 'transient' state. " \
                    "put it in the session to be able to get filters " \
                    "and perform queries." % obj
        return session

    def filter_descendants(self, and_self=False):
        """
        Get a filter condition for node's descendants.

        Requires that node has `path`, `tree_id` and `depth` values
        available (that means it has "persistent version" even if the
        node itself is in "detached" state or it is in "pending" state
        in `autoflush`-enabled session).

        Usage example::

            session.query(Node).filter(root.mp.filter_descendants()) \\
                               .order_by(Node.mp)

        This example is silly and only shows an approach of using
        `filter_descendants`, dont use it for such purpose as there is a
        better way for such simple queries: :meth:`query_descendants`.

        :param and_self:
            `bool`, if set to `True` self node will be selected by filter.
        :return:
            a filter clause applicable as argument for
            `sqlalchemy.orm.Query.filter()` and others.
        """
        opts = self._mp_opts
        obj = self._get_obj()
        self._get_session_and_assert_flushed(obj)
        path = getattr(obj, opts.path_field.name)
        # we are not use queries like `WHERE path LIKE '0.1.%` instead
        # they looks like `WHERE path > '0.1' AND path < '0.2'`
        try:
            next_sibling_path = inc_path(path, opts.steplen)
        except PathOverflowError:
            # this node is theoretically last, will not check
            # for `path < next_sibling_path`
            next_sibling_path = None
        tree_id = getattr(obj, opts.tree_id_field.name)
        # always filter by `tree_id`:
        filter_ = opts.tree_id_field == tree_id
        if and_self:
            # non-strict inequality if this node should satisfy filter
            filter_ &= opts.path_field >= path
        else:
            filter_ &= opts.path_field > path
        if next_sibling_path is not None:
            filter_ &= opts.path_field < next_sibling_path
        return filter_

    def query_descendants(self, session=None, and_self=False):
        """
        Get a query for node's descendants.

        Requires that node is in "persistent" state or in "pending"
        state in `autoflush`-enabled session.

        :param session:
            session object for query. If not provided, node's session is
            used. If node is in "detached" state and :attr:`session` is
            not provided, query will be detached too (will require setting
            `session` attribute to execute).
        :param and_self:
            `bool`, if set to `True` self node will be selected by query.
        :return:
            a `sqlalchemy.orm.Query` object which contains only node's
            descendants and is ordered by `path`.
        """
        query = self._get_query(self._get_obj(), session) \
                    .filter(self.filter_descendants(and_self=and_self)) \
                    .order_by(self._mp_opts.order_by_clause())
        return query

    def filter_children(self):
        """
        The same as :meth:`filter_descendants` but filters children nodes
        and does not accepts :attr:`and_self` parameter.
        """
        opts = self._mp_opts
        obj = self._get_obj()
        self._get_session_and_assert_flushed(obj)
        depth = getattr(obj, opts.depth_field.name) + 1
        # Oh yeah, using adjacency relation may be more efficient here. But
        # one can access AL-based children collection without `sqlamp` at all.
        # And in that case we can be sure that at least `(tree_id, path)`
        # index is used. `parent_id` field may not have index set up so
        # condition `pk == parent_id` in SQL query may be even less efficient.
        return self.filter_descendants() & (opts.depth_field == depth)

    def query_children(self, session=None):
        """
        The same as :meth:`query_descendants` but queries children nodes and
        does not accepts :attr:`and_self` parameter.
        """
        query = self._get_query(self._get_obj(), session) \
                    .filter(self.filter_children()) \
                    .order_by(self._mp_opts.order_by_clause())
        return query

    def filter_ancestors(self, and_self=False):
        "The same as :meth:`filter_descendants` but filters ancestor nodes."
        opts = self._mp_opts
        obj = self._get_obj()
        self._get_session_and_assert_flushed(obj)
        tree_id = getattr(obj, opts.tree_id_field.name)
        depth = getattr(obj, opts.depth_field.name)
        path = getattr(obj, opts.path_field.name)
        # WHERE tree_id = <node.tree_id> AND <node.path> LIKE path || '%'
        filter_ = (opts.tree_id_field == tree_id) \
                  & sqlalchemy.sql.expression.literal(
                        path, sqlalchemy.String
                    ).like(opts.path_field + '%')
        if and_self:
            filter_ &= opts.depth_field  <= depth
        else:
            filter_ &= opts.depth_field < depth
        return filter_

    def query_ancestors(self, session=None, and_self=False):
        "The same as :meth:`query_descendants` but queries node's ancestors."
        query = self._get_query(self._get_obj(), session) \
                    .filter(self.filter_ancestors(and_self=and_self)) \
                    .order_by(self._mp_opts.depth_field)
        return query

    def filter_parent(self):
        "Get a filter condition for a node's parent."
        opts = self._mp_opts
        obj = self._get_obj()
        self._get_session_and_assert_flushed(obj)
        parent_id = getattr(obj, opts.parent_id_field.name)
        if parent_id is None:
            return sqlalchemy.sql.literal(False)
        filter_ = opts.pk_field == parent_id
        return filter_


class MPManager(object):
    """
    Descriptor for access class-level and instance-level API.

    Basic usage is simple::

        class Node(object):
            mp = sqlamp.MPManager(node_table)

    Now there is an ability to get instance manager or class manager
    via property `'mp'` depending on way to access it. `Node.mp` will
    return mapper extension till class is mapped, class manager
    :class:`MPClassManager` after that and `instance_node.mp`
    will return instance_node's :class:`MPInstanceManager`.
    See that classes for more details about their public API.

    .. versionchanged:: 0.5.1
        Previously mapper extension was accessible via class manager's
        property.

    :param table:
        instance of `sqlalchemy.Table`. A table that will be mapped to
        node class and will hold tree nodes in its rows. It is the only
        one strictly required argument.

    :param parent_id_field=None:
        a foreign key field that is reference to parent node's
        primary key. If this parameter is omitted, it will be guessed
        joining a `table` with itself and using the right part of join's
        onclause as parent id field.

    :param path_field='mp_path':
        the hame for the path field or the field object itself. The field
        will be created if the actual parameter value is a string and
        there is no such column in the table `table`. If value provided
        is an object column some sanity checks will be performed with
        the column object: it should have `nullable=False` and have
        :class:`PathField` type.

    :param depth_field='mp_depth':
        the same as for :attr:`path_field`, except that the type of this
        column should be :class:`DepthField`.

    :param tree_id_field='mp_tree_id':
        the same as for :attr:`path_field`, except that the type of this
        column should be :class:`TreeIdField`.

    :param steplen=3:
        an integer, the number of characters in each part of the path.
        This value allows to fine-tune the limits for max tree depth
        (equal to `(255 / steplen) + 1`) and max children in each node
        (`36 ** steplen`). Default `3` value sets the following limits:
        max depth is `86` and max children number is `46656`.

    :param instance_manager_key='_mp_instance_manager':
        name for node instance's attribute to cache node's instance
        manager.

    .. warning::
        Do not change the values of `MPManager` constructor's attributes
        after saving a first tree node. Doing this will corrupt the tree.
    """
    def __init__(self, *args, **kwargs):
        self.instance_manager_key = kwargs.pop('instance_manager_key', \
                                               '_mp_instance_manager')
        opts = MPOptions(*args, **kwargs)
        self._mp_opts = opts
        self.class_manager = None
        self.mapper_extension = MPMapperExtension(opts=opts)
        self.root_node_class = None

    def __get__(self, obj, objtype):
        """
        There may be three kinds of return values from this getter.

        The first one is used when the class which this descriptor
        is attached to is not yet mapped to any table. In that case
        the return value is an instance of :class:`MPMapperExtension`.
        which is intended to be used as mapper extension.

        The second scenario is access to :class:`MPManager` via mapped
        class. The corresponding :class:`MPInstanceManager`'s instance
        is returned.

        .. note:: If the nodes of your tree use polymorphic inheritance
                  it is important to know that class manager is accessible
                  only via the base class of inheritance hierarchy.

        And the third way is accessing it from the node instance.
        Attached to that node :class:`instance manager <MPInstanceManager>`
        is returned then.
        """
        if obj is None:
            try:
                root_node_class = self.get_root_node_class(objtype)
            except sqlalchemy.orm.exc.UnmappedClassError:
                return self.mapper_extension
            assert objtype is root_node_class, \
                   "MPClassManager should be accessed via base class in the " \
                   "polymorphic inheritance hierarchy: %r" % root_node_class
            if self.class_manager is None:
                self.class_manager = MPClassManager(objtype, self._mp_opts)
            return self.class_manager
        else:
            instance_manager = obj.__dict__.get(self.instance_manager_key)
            if instance_manager is None:
                root_node_class = self.get_root_node_class(objtype)
                instance_manager = MPInstanceManager(
                    self._mp_opts, root_node_class, obj
                )
                obj.__dict__[self.instance_manager_key] = instance_manager
            return instance_manager

    def get_root_node_class(self, objtype):
        """
        Get the root node class in the polymorphic inheritance hierarchy.
        """
        if self.root_node_class is None:
            mapper = class_mapper(objtype)
            while mapper.inherits is not None:
                mapper = mapper.inherits
            self.root_node_class = mapper.class_
        return self.root_node_class


_nonexistent = object()
def _iter_current_next(sequence):
    """
    Generate `(current, next)` tuples from sequence. Last tuple will
    have `_nonexistent` object at the second place.

    >>> x = _iter_current_next('1234')
    >>> x.next(), x.next(), x.next()
    (('1', '2'), ('2', '3'), ('3', '4'))
    >>> x.next() == ('4', _nonexistent)
    True
    >>> list(_iter_current_next(''))
    []
    >>> list(_iter_current_next('1')) == [('1', _nonexistent)]
    True
    """
    iterator = iter(sequence)
    current_item = iterator.next()
    while current_item != _nonexistent:
        try:
            next_item = iterator.next()
        except StopIteration:
            next_item = _nonexistent
        yield (current_item, next_item)
        current_item = next_item

def _recursive_iterator(sequence, is_child_func):
    """
    Make a recursive iterator from plain sequence using :attr:`is_child_func`
    to determine parent-children relations. Works right only if used in
    depth-first recursive consumer.

    :param is_child_func:
        a callable object which accepts two positional arguments and
        returns `True` value if first argument value is parent of second
        argument value.

    >>> is_child_func = lambda parent, child: child > parent
    >>> def listify(seq):
    ...     return [(node, listify(children)) for node, children in seq]
    >>> listify(_recursive_iterator('ABCABB', is_child_func))
    [('A', [('B', [('C', [])])]), ('A', [('B', []), ('B', [])])]
    >>> listify(_recursive_iterator('', is_child_func))
    []
    >>> _recursive_iterator('A', is_child_func).next()
    ('A', ())
    >>> _recursive_iterator('AB', is_child_func).next() # doctest: +ELLIPSIS
    ('A', <generator object ...>)
    """
    current_next_iterator = _iter_current_next(sequence)
    item = {}
    is_parent_of_next = lambda node: \
            item['next'] is not _nonexistent \
            and is_child_func(node, item['next'])

    def step():
        item['current'], item['next'] = current_next_iterator.next()
        if is_parent_of_next(item['current']):
            return (item['current'], children_generator(item['current']))
        else:
            return (item['current'], tuple())

    def children_generator(parent_node):
        while True:
            yield step()
            if not is_parent_of_next(parent_node):
                break

    while True:
        yield step()


def tree_recursive_iterator(flat_tree, class_manager):
    """
    Make a recursive iterator from plain tree nodes sequence (`Query`
    instance for example). Generates two-item tuples: node itself
    and it's children collection (which also generates two-item tuples...)
    Children collection evaluates to ``False`` if node has no children
    (it is zero-length tuple for leaf nodes), else it is a generator object.

    :param flat_tree: plain sequence of tree nodes.
    :param class_manager: instance of :class:`MPClassManager`

    Can be used when it is simpler to process tree structure recursively.
    Simple usage example::

        def recursive_tree_processor(nodes):
            print '<ul>'
            for node, children in nodes:
                print '<li>%s' % node.name,
                if children:
                    recursive_tree_processor(children)
                print '</li>'
            print '</ul>'

        query = root_node.mp.query_descendants(and_self=True)
        recursive_tree_processor(
            sqlamp.tree_recursive_iterator(query, Node.mp)
        )

    If `flat_tree` is a `sqlalchemy.orm.Query` instance, it will be ordered
    by `class_manager`. If it is plain list, do not forget that such ordering
    is strictly required for `tree_recursive_iterator()` to work right.

    .. warning:: Process `flat_tree` items once and sequentially so works
      right only if used in depth-first recursive consumer.
    """
    opts = class_manager._mp_opts
    tree_id = attrgetter(opts.tree_id_field.name)
    depth = attrgetter(opts.depth_field.name)
    def is_child(parent, child):
        return tree_id(parent) == tree_id(child) \
                and depth(child) == depth(parent) + 1
    if isinstance(flat_tree, sqlalchemy.orm.Query):
        flat_tree = flat_tree.order_by(class_manager)
    return _recursive_iterator(flat_tree, is_child)


class DeclarativeMeta(BaseDeclarativeMeta):
    """
    Metaclass for declaratively defined node model classes.

    .. versionadded:: 0.5

    See :ref:`usage example <declarative>` above in Quickstart.

    All options that accepts :class:`MPManager` can be provided
    with declarative definition. To provide an option you can
    simply assign value to class' property with name like
    ``__mp_tree_id_field__`` (for ``tree_id_field`` parameter)
    and so forth. See the complete list of options in :class:`MPManager`'s
    constructor parameters. Note that you can use only string options
    for field names, not the column objects.

    A special class variable ``__mp_manager__`` should exist and hold
    a string name which will be used as `MPManager` descriptor property.
    """
    def __init__(cls, name, bases, dct):
        if not hasattr(cls, '__mp_manager__'):
            super(DeclarativeMeta, cls).__init__(name, bases, dct)
            return
        mp_manager_name = cls.__mp_manager__

        # preventing the property to be inherited
        del cls.__mp_manager__

        opts = {}
        for opt, default in [
                ('path_field', 'mp_path'),
                ('depth_field', 'mp_depth'),
                ('tree_id_field', 'mp_tree_id'),
                ('steplen', 3),
                ('instance_manager_key', '_mp_instance_manager')
            ]:
            optname = '__mp_%s__' % opt
            if hasattr(cls, optname):
                opts[opt] = getattr(cls, optname)
                delattr(cls, optname)
            else:
                opts[opt] = default

        for field, ftype in [
                ('path_field', PathField),
                ('depth_field', DepthField),
                ('tree_id_field', TreeIdField)
            ]:
            assert isinstance(opts[field], basestring)
            if not hasattr(cls, opts[field]):
                column = sqlalchemy.Column(ftype(), nullable=False)
                # SQLAlchemy 0.5.x needs this:
                dct[opts[field]] = column
                # and SQLAlchemy 0.6/.x needs this:
                setattr(cls, opts[field], column)
        super(DeclarativeMeta, cls).__init__(name, bases, dct)
        mp_manager = MPManager(cls.__table__, **opts)
        setattr(cls, mp_manager_name, mp_manager)
        mp_class_manager = getattr(cls, mp_manager_name)
        cls.__mapper__.extension.append(mp_manager.mapper_extension)

