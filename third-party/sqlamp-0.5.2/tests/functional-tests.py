#!/usr/bin/env python
"""
`sqlamp` functional tests.
"""
import random
import unittest

import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
import sqlamp

import tests._testlib as _testlib
_testlib.setup()
from tests._testlib import Cls, make_session, tbl, metadata


class FunctionalTestCase(_testlib._BaseTestCase):
    name_pattern = [
        ("root1", [
            ("child11", []),
            ("child12", []),
            ("child13", []),
        ]),
        ("root2", [
            ("child21", [
                ("child211", []),
                ("child212", [
                    ("child2121", []),
                    ("child2122", [
                        ("child21221", []),
                        ("child21222", []),
                    ]),
                ]),
            ]),
            ("child22", []),
            ("child23", []),
        ]),
        ("root3", []),
    ]

    def test_insert_roots(self):
        o, o2, o3 = Cls(), Cls(), Cls()
        self.sess.add_all([o, o2, o3])
        self.sess.commit()
        self.assertTrue(o2 in self.sess)
        self.assertFalse(o2 in self.sess.dirty)

        o1, o2, o3 = self.sess.query(Cls).order_by('id').all()
        self.assertEqual(o1.mp_tree_id, 1)
        self.assertEqual(o2.mp_tree_id, 2)
        self.assertEqual(o3.mp_tree_id, 3)

        for o in [o1, o2, o3]:
            self.assertEqual(o.mp_path, '')
            self.assertEqual(o.mp_depth, 0)

    def test_insert_children(self):
        parent = Cls()
        self.sess.add(parent)
        self.sess.flush()

        children = Cls(), Cls(), Cls()
        for child in children:
            child.parent = parent
        self.sess.add_all(children)
        self.sess.commit()
        self.sess.expunge_all()

        parent, c1, c2, c3 = self.sess.query(Cls).order_by('id').all()
        for child in [c1, c2, c3]:
            self.assertEqual(child.mp_tree_id, parent.mp_tree_id)
            self.assertEqual(child.mp_depth, 1)
        self.assertEqual(c1.mp_path, '00')
        self.assertEqual(c2.mp_path, '01')
        self.assertEqual(c3.mp_path, '02')

        children = Cls(), Cls(), Cls()
        for child in children:
            child.parent = c1
        self.sess.add_all(children)
        self.sess.commit()

        for child in children:
            self.assertEqual(child.mp_tree_id, parent.mp_tree_id)
            self.assertEqual(child.mp_depth, 2)
        self.assertEqual(children[0].mp_path, c1.mp_path + '00')
        self.assertEqual(children[1].mp_path, c1.mp_path + '01')
        self.assertEqual(children[2].mp_path, c1.mp_path + '02')

    def _fill_tree(self):
        def _create_node(name, parent=None):
            node = Cls(name=name, parent=parent)
            self.sess.add(node)
            self.sess.flush()
            return node

        def _process_node(node, parent=None):
            name, children = node
            node = _create_node(name, parent)
            for child in children:
                _process_node(child, node)

        for node in self.name_pattern:
            _process_node(node)
        self.sess.commit()

    def _corrupt_tree(self, including_roots):
        root1, root2, root3 = self.sess.query(Cls).filter_by(parent=None) \
                                                  .order_by('name')
        # corrupting path:
        used_pathes = set() # remember that they should be unique
        for node in root1.mp.query_descendants():
            while True:
                path = ''.join(
                    random.sample(
                        sqlamp.ALPHABET + '!@#$%^&*', random.randint(1, 40)
                    )
                )
                if not path in used_pathes:
                    used_pathes.add(path)
                    break
            node.mp_path = path
        if including_roots:
            root1.mp_path = '[][][]'
        # depth:
        for node in root2.mp.query_descendants():
            node.mp_depth = random.randint(10, 90)
        if including_roots:
            root2.mp_depth = 100
        # tree_id:
        for node in root3.mp.query_descendants():
            node.mp_tree_id = _from = random.randint(1, 2000)
        if including_roots:
            root3.mp_tree_id = 42 + root3.mp_tree_id

        self.sess.flush()
        self.sess.expire_all()
        return [root1, root2, root3]

    def test_rebuild_all_trees(self):
        self._fill_tree()
        query = sqlalchemy.select([tbl]).order_by(tbl.c.id)
        data_before = query.execute().fetchall()
        self._corrupt_tree(including_roots=True)
        # rebuilding all trees:
        Cls.mp.rebuild_all_trees()
        # all trees should be in consistent state
        # and be absolutely the same as before corruption.
        data_after = query.execute().fetchall()
        self.assertEqual(data_before, data_after)

    def test_rebuild_subtree(self):
        self._fill_tree()
        query = sqlalchemy.select([tbl]).order_by(tbl.c.id)
        data_before = query.execute().fetchall()
        roots = self._corrupt_tree(including_roots=False)
        # rebuilding each tree:
        for root in roots:
            Cls.mp.rebuild_subtree(root.id, tbl.c.id)
        # all trees should be in consistent state
        # and be absolutely the same as before corruption.
        data_after = query.execute().fetchall()
        self.assertEqual(data_before, data_after)

    def test_descendants(self):
        self._fill_tree()
        child212 = self.sess.query(Cls).filter_by(name='child212').one()
        descendants = self.sess.query(Cls).filter(
            child212.mp.filter_descendants(and_self=False)
        ).order_by(Cls.mp).all()
        self.assertEqual(descendants, child212.mp.query_descendants().all())
        should_be = self.sess.query(Cls).filter(
            tbl.c.name.in_(
                ("child2121", "child2122", "child21221", "child21222")
            )
        ).order_by(Cls.mp).all()
        self.assertEqual(descendants, should_be)
        descendants_and_self = self.sess.query(Cls).filter(
            child212.mp.filter_descendants(and_self=True)
        ).order_by(Cls.mp).all()
        self.assertEqual(
            descendants_and_self,
            child212.mp.query_descendants(and_self=True).all()
        )
        self.assertEqual(descendants_and_self, [child212] + should_be)

    def test_children(self):
        self._fill_tree()
        root2 = self.sess.query(Cls).filter_by(name='root2').one()
        children = self.sess.query(Cls).filter(
            root2.mp.filter_children()
        ).order_by(Cls.mp).all()
        should_be = self.sess.query(Cls).filter(
            tbl.c.name.in_(("child21", "child22", "child23"))
        ).order_by(Cls.mp).all()
        self.assertEqual(children, should_be)
        self.assertEqual(children, root2.mp.query_children().all())

    def test_filter_parent(self):
        self._fill_tree()
        root1 = self.sess.query(Cls).filter_by(name='root1').one()
        self.assertEqual(
            self.sess.query(Cls).filter(root1.mp.filter_parent()).count(), 0
        )
        for child in root1.mp.query_children():
            self.assertEqual(
                self.sess.query(Cls).filter(child.mp.filter_parent()).one(),
                root1
            )

    def test_ancestors(self):
        self._fill_tree()
        child2122 = self.sess.query(Cls).filter_by(name='child2122').one()
        ancestors = self.sess.query(Cls).filter(
            child2122.mp.filter_ancestors()
        ).order_by(Cls.mp).all()
        should_be = self.sess.query(Cls).filter(
            tbl.c.name.in_(("child212", "child21", "child2", "root2"))
        ).order_by(Cls.mp).all()
        self.assertEqual(ancestors, should_be)
        self.assertEqual(ancestors, child2122.mp.query_ancestors().all())
        ancestors_and_self = self.sess.query(Cls).filter(
            child2122.mp.filter_ancestors(and_self=True)
        ).order_by(Cls.mp).all()
        self.assertEqual(ancestors_and_self, should_be + [child2122])
        self.assertEqual(
            ancestors_and_self,
            child2122.mp.query_ancestors(and_self=True).all()
        )

    def test_too_many_children_and_last_child_descendants(self):
        self.assertEqual(Cls.mp.max_children, 1296) # 36 ** 2
        root = Cls()
        self.sess.add(root)
        self.sess.commit()
        for x in xrange(1296):
            self.sess.add(Cls(parent=root, name=str(x)))
        self.sess.commit()
        self.sess.add(Cls(parent=root))
        self.assertRaises(sqlamp.TooManyChildrenError, self.sess.flush)
        self.sess.rollback()
        last_child = self.sess.query(Cls).filter_by(name='1295').one()
        last_childs_child = Cls(parent=last_child, name='1295.1')
        self.sess.add(last_childs_child)
        self.sess.flush()
        self.assertEqual(
            last_child.mp.query_descendants().all(), [last_childs_child]
        )

    def test_path_too_deep(self):
        self.assertEqual(Cls.mp.max_depth, 128) # int(255 / 2) + 1
        node = None
        for x in xrange(128):
            new_node = Cls(parent=node)
            self.sess.add(new_node)
            self.sess.flush()
            node = new_node
        self.sess.add(Cls(parent=node))
        self.assertRaises(sqlamp.PathTooDeepError, self.sess.flush)

    def test_query_all_trees(self):
        self._fill_tree()
        all_trees = Cls.mp.query_all_trees(self.sess)
        self.assertEqual(
            [node.name for node in all_trees],
            ["root1", "child11", "child12", "child13", "root2", "child21",
             "child211", "child212", "child2121", "child2122",
             "child21221", "child21222", "child22", "child23", "root3"]
        )

    def test_tree_recursive_iterator(self):
        self._fill_tree()
        all_trees = Cls.mp.query_all_trees(self.sess)
        all_trees = sqlamp.tree_recursive_iterator(all_trees, Cls.mp)
        def listify(recursive_iterator):
            return [(node.name, listify(children))
                    for node, children in recursive_iterator]
        self.assertEqual(self.name_pattern, listify(all_trees))

    def test_declarative(self):
        BaseNode = declarative_base(metadata=metadata, \
                                    metaclass=sqlamp.DeclarativeMeta)
        class Node(BaseNode):
            __tablename__ = 'node'
            __mp_manager__ = 'MP'
            __mp_steplen__ = 5
            __mp_depth_field__ = 'MP_depth'
            id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
            parent_id = sqlalchemy.Column(sqlalchemy.ForeignKey('node.id'))
            parent = sqlalchemy.orm.relation("Node", remote_side=[id])
            name = sqlalchemy.Column(sqlalchemy.String(100))

        Node.__table__.create()

        try:
            root = Node()
            self.assert_(isinstance(root.MP, sqlamp.MPInstanceManager))
            self.sess.add(root)
            self.sess.commit()
            child = Node()
            child.parent = root
            self.sess.add(child)
            self.sess.commit()

            [root, child] = self.sess.query(Node).order_by('id').all()
            self.assertEqual(root.mp_path, '')
            self.assertEqual(root.MP_depth, 0)
            self.assertEqual(child.mp_path, '00000')
            self.assertEqual(child.MP_depth, 1)
        finally:
            Node.__table__.delete()

    def test_implicit_pk_fk(self):
        tbl = sqlalchemy.Table('tbl2', metadata,
            sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
            sqlalchemy.Column('pid', sqlalchemy.ForeignKey('tbl2.id'))
        )
        mpm = sqlamp.MPManager(tbl)
        self.assertEqual(tbl.c.id, mpm._mp_opts.pk_field)
        self.assertEqual(tbl.c.pid, mpm._mp_opts.parent_id_field)

    def test_table_inheritance(self):
        tbl_abstract = sqlalchemy.Table('tbl_abstract', metadata,
            sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
            sqlalchemy.Column('parent_id',
                              sqlalchemy.ForeignKey('tbl_abstract.id')),
            sqlalchemy.Column('type', sqlalchemy.String(100), nullable=False)
        )
        tbl_sub = sqlalchemy.Table('tbl_sub', metadata,
            sqlalchemy.Column('id', sqlalchemy.ForeignKey('tbl_abstract.id'),
                              primary_key=True)
        )

        class AbstractNode(object):
            mp = sqlamp.MPManager(tbl_abstract)
        sqlalchemy.orm.mapper(
            AbstractNode, tbl_abstract, polymorphic_on=tbl_abstract.c.type,
            polymorphic_identity='abstract',
            extension=[AbstractNode.mp]
        )

        class SubNode(AbstractNode):
            pass
        sqlalchemy.orm.mapper(SubNode, tbl_sub, inherits=AbstractNode,
                              polymorphic_identity='sub')

        tbl_abstract.create()
        tbl_sub.create()

        try:
            abstract_node = AbstractNode()
            self.sess.add(abstract_node); self.sess.commit()
            sub_node = SubNode()
            sub_node.parent_id = abstract_node.id
            self.sess.add(sub_node); self.sess.commit()
            [a, s] = AbstractNode.mp.query_all_trees(self.sess)
            self.assert_(a is abstract_node)
            self.assert_(s is sub_node)
        finally:
            tbl_abstract.delete()
            tbl_sub.delete()

    def test_table_inheritance_declarative(self):
        BaseNode = declarative_base(metadata=metadata, \
                                    metaclass=sqlamp.DeclarativeMeta)
        class AbstractNode(BaseNode):
            __tablename__ = 'node2'
            __mp_manager__ = 'mp'
            id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
            parent_id = sqlalchemy.Column(sqlalchemy.ForeignKey('node2.id'))
            type = sqlalchemy.Column(sqlalchemy.String(100), nullable=False)
            __mapper_args__ = {'polymorphic_on': type,
                               'polymorphic_identity': 'abs'}
        class SubNode(AbstractNode):
            __tablename__ = 'node2sub'
            __mapper_args__ = {'polymorphic_identity': 'sub'}
            id = sqlalchemy.Column(sqlalchemy.ForeignKey('node2.id'),
                                   primary_key=True)
        class SubNode2(AbstractNode):
            __tablename__ = 'node2sub2'
            __mapper_args__ = {'polymorphic_identity': 'sub2'}
            id = sqlalchemy.Column(sqlalchemy.ForeignKey('node2.id'),
                                   primary_key=True)

        AbstractNode.__table__.create()
        SubNode.__table__.create()
        SubNode2.__table__.create()

        try:
            abstract_node = AbstractNode()
            self.sess.add(abstract_node); self.sess.commit()

            sub_node = SubNode()
            sub_node.parent_id = abstract_node.id
            self.sess.add(sub_node); self.sess.commit()

            sub_node2 = SubNode2()
            sub_node2.parent_id = sub_node.id
            self.sess.add(sub_node2); self.sess.commit()

            [a, s, s2] = AbstractNode.mp.query_all_trees(self.sess)
            self.assert_(a is abstract_node)
            self.assert_(s is sub_node)
            self.assert_(s2 is sub_node2)

            [s2] = s.mp.query_descendants()
            self.assert_(s2 is sub_node2)
        finally:
            AbstractNode.__table__.delete()
            SubNode.__table__.delete()
            SubNode2.__table__.delete()


def get_suite():
    return unittest.TestLoader().loadTestsFromTestCase(FunctionalTestCase)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(get_suite())

