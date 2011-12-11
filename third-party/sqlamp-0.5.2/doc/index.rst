.. automodule:: sqlamp

----------
Quickstart
----------

.. note:: Code examples here are all runable by copy-paste
          to interactive interpreter.

.. code-block:: python

    import sqlalchemy, sqlalchemy.orm
    engine = sqlalchemy.create_engine('sqlite:///:memory:', echo=False)
    metadata = sqlalchemy.MetaData(engine)

    node_table = sqlalchemy.Table('node', metadata,
        sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
        sqlalchemy.Column('parent_id', sqlalchemy.ForeignKey('node.id')),
        sqlalchemy.Column('name', sqlalchemy.String)
    )

There is nothing special to :mod:`sqlamp` here. Note self-reference
"child to parent" ('parent_id' is foreign key to table's primary key)
just as in any other implementation of adjacency relations.

.. code-block:: python

    import sqlamp
    class Node(object):
        mp = sqlamp.MPManager(node_table)
        def __init__(self, name, parent=None):
            self.name = name
            self.parent = parent
        def __repr__(self):
            return '<Node %r>' % self.name

Attach instance of :class:`~sqlamp.MPManager` to class that represents
node. The only required argument for :class:`~sqlamp.MPManager` constructor
is the table object.

Now we can create the table and define the mapper (it is important
to create table *after* :class:`~sqlamp.MPManager` was created as
created :class:`~sqlamp.MPManager` appends three new columns and one index
to the table):

.. code-block:: python

    node_table.create()

Setting up the mapper requires only one extra step --- providing `Node.mp`
as mapper extension:

.. code-block:: python

    mapper = sqlalchemy.orm.mapper(
        Node, node_table,
        extension=[Node.mp],
        properties={
            'parent': sqlalchemy.orm.relation(
                Node, remote_side=[node_table.c.id]
            )
        }
    )

You may see value provided as `properties` argument: this is a way `recomended
<http://www.sqlalchemy.org/docs/05/mappers.html#adjacency-list-relationships>`_
by the official SQLAlchemy documentation to set up an adjacency relation.


.. _declarative:

.. rubric:: Alternative way to set up: ext.declarative

Starting from version 0.5 it is able and convenient to use declarative
approach to set your trees up:

.. code-block:: python

    import sqlalchemy, sqlalchemy.orm
    from sqlalchemy.ext.declarative import declarative_base
    import sqlamp

    engine = sqlalchemy.create_engine('sqlite:///:memory:', echo=False)
    metadata = sqlalchemy.MetaData(engine)

    BaseNode = declarative_base(metadata=metadata,
                                metaclass=sqlamp.DeclarativeMeta)

    class Node(BaseNode):
        __tablename__ = 'node'
        __mp_manager__ = 'mp'
        id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        parent_id = sqlalchemy.Column(sqlalchemy.ForeignKey('node.id'))
        parent = sqlalchemy.orm.relation("Node", remote_side=[id])
        name = sqlalchemy.Column(sqlalchemy.String())
        def __init__(self, name, parent=None):
            self.name = name
            self.parent = parent
        def __repr__(self):
            return '<Node %r>' % self.name

    Node.__table__.create()

As you can see it is pretty much the same as usual for `sqlalchemy's
"declarative" extension
<http://www.sqlalchemy.org/docs/05/reference/ext/declarative.html>`_.
Only two things here are sqlamp-special: ``metaclass`` argument provided
to ``declarative_base()`` factory function should be :class:`DeclarativeMeta`
and the node class should have an ``__mp_manager__`` property with string
value. See :class:`DeclarativeMeta` for more information about options.

Now all the preparation steps are done. Lets try to use it!

.. code-block:: python

    session = sqlalchemy.orm.sessionmaker(engine)()
    root = Node('root')
    child1 = Node('child1', parent=root)
    child2 = Node('child2', parent=root)
    grandchild = Node('grandchild', parent=child1)
    session.add_all([root, child1, child2, grandchild])
    session.flush()

We have just created a sample tree. This is all about `AL`, nothing
special to :mod:`sqlamp` here. The interesting part is fetching trees:

.. code-block:: python

    root.mp.query_children().all()
    # should print [<Node 'child1'>, <Node 'child2'>]

    root.mp.query_descendants().all()
    # [<Node 'child1'>, <Node 'grandchild'>, <Node 'child2'>]

    grandchild.mp.query_ancestors().all()
    # [<Node 'root'>, <Node 'child1'>]

    session.query(Node).order_by(Node.mp).all()
    # [<Node 'root'>, <Node 'child1'>, <Node 'grandchild'>, <Node 'child2'>]

    for node in root.mp.query_descendants(and_self=True):
        print '  ' * node.mp_depth, node.name
    # root
    #   child1
    #     grandchild
    #   child2

As you can see all `sqlamp` functionality is accessible via `MPManager`
descriptor (called `'mp'` in this example).

*Note*: ``Node.mp`` (a so-called "class manager") is not the same
as ``node.mp`` ("instance manager"). Do not confuse them as they are for
different purposes and their APIs has no similar. Class manager (see
:class:`MPClassManager`) used to features that are not intended
to particular node but for the whole tree: basic setup (mapper
extension) and tree-maintainance functions. And an instance managers
(:class:`MPInstanceManager`) are each unique to and bounded to a node.
They are implements a queries for a related nodes and other things
specific to concrete node. There is also third kind of values
that ``MPManager`` descriptor may return, see :class:`its reference
<MPManager>` for more info.


----------------------
Implementation details
----------------------
:mod:`sqlamp` had borrowed some implementation ideas from `django-treebeard`_.
In particular, `sqlamp` uses the same alphabet (which consists of numeric
digits and latin-letters in upper case), `sqlamp` as like as `django-treebeard`
doesn't use path parts delimiter --- path parts has fixed adjustable length.
But unlike `django-treebeard` `sqlamp` stores each tree absolutelly
stand-alone --- two or more trees may (and will) have identical values in
`path` and `depth` fields and be different only by values in `tree_id` field.
This is the way that can be found in `django-mptt`_.

:mod:`sqlamp` works *only* on basis of Adjacency Relations. This solution
makes data more denormalized but more fault-tolerant. It is able to rebuild
all pathes for all trees using only `AL` data. Also it makes applying `sqlamp`
on existing project easer.

.. _`django-treebeard`: http://django-treebeard.googlecode.com/
.. _`django-mptt`: http://django-mptt.googlecode.com/


-------
Support
-------
Feel free to `email author <anton@angri.ru>`_ directly to send bugreports,
feature requests, patches or just to say "thanks"! :)


-------------
API Reference
-------------

.. autoexception:: PathOverflowError
.. autoexception:: TooManyChildrenError
.. autoexception:: PathTooDeepError

.. autoclass:: MPManager(table, parent_id_field=None, path_field='mp_path', depth_field='mp_depth', tree_id_field='mp_tree_id', steplen=3, instance_manager_key='_mp_instance_manager')
    :members: __get__

.. autoclass:: DeclarativeMeta


.. autoclass:: MPClassManager
    :members:

    .. automethod:: __clause_element__


.. autoclass:: MPInstanceManager
    :members: filter_descendants, query_descendants, filter_children, query_children, filter_ancestors, query_ancestors

.. autofunction:: tree_recursive_iterator

.. autoclass:: PathField()
.. autoclass:: DepthField()
.. autoclass:: TreeIdField()


---------
Changelog
---------
.. include:: ../CHANGES


.. toctree::
   :maxdepth: 2


