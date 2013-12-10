# -*- coding: utf-8 -*-
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Modified mercurial DAG graph functions that re-uses VCS structure

It allows to have a shared codebase for DAG generation for hg and git repos
"""

nullrev = -1

def _first_known_ancestors(parentrev_func, minrev, knownrevs, head):
    """
    Walk DAG defined by parentrev_func.
    Return most immediate ancestors of head that are in knownrevs.
    minrev is lower bound on knownrevs.
    """
    pending = set([head])
    seen = set()
    ancestors = set()
    while pending:
        r = pending.pop()
        if r < minrev:
            pass
        elif r in knownrevs:
            ancestors.add(r)
        elif r not in seen:
            pending.update(parentrev_func(r))
            seen.add(r)
    return ancestors

def graph_data(repo, revs):
    """Return a DAG with colored edge information for revs

    For each DAG node this function emits tuples::

      ((col, color), [(col, nextcol, color)])

    with the following new elements:

      - Tuple (col, color) with column and color index for the current node
      - A list of tuples indicating the edges between the current node and its
        parents.
    """
    dag = _dagwalker(repo, revs)
    return list(_colored(dag))

def _dagwalker(repo, revs):
    if not revs:
        return

    if repo.alias == 'hg':
        parentrev_func = repo._repo.changelog.parentrevs
    elif repo.alias == 'git':
        def parentrev_func(rev):
            return [x.revision for x in repo[rev].parents]

    minrev = revs[-1] # assuming sorted reverse
    knownrevs = set(revs)
    acache = {}
    for rev in revs:
        parents = set(parentrev_func(rev)) - set([nullrev])
        dagparents = parents & knownrevs
        # Calculate indirect parents
        for p in parents - dagparents:
            ancestors = acache.get(p)
            if ancestors is None:
                ancestors = acache[p] = _first_known_ancestors(parentrev_func, minrev, knownrevs, p)
            dagparents.update(ancestors)

        yield (rev, sorted(dagparents))


def _colored(dag):
    """annotates a DAG with colored edge information

    For each DAG node this function emits tuples::

      ((col, color), [(col, nextcol, color)])

    with the following new elements:

      - Tuple (col, color) with column and color index for the current node
      - A list of tuples indicating the edges between the current node and its
        parents.
    """
    row = []
    colors = {}
    newcolor = 1

    for (rev, dagparents) in dag:

        # Compute row and nextrow
        if rev not in row:
            row.append(rev)  # new head
            colors[rev] = newcolor
            newcolor += 1

        nextrow = row[:]

        # Add unknown parents to nextrow
        addparents = [p for p in dagparents if p not in nextrow]
        col = nextrow.index(rev)
        nextrow[col:col + 1] = addparents

        # Set colors for the parents
        color = colors.pop(rev)
        for i, p in enumerate(addparents):
            if not i:
                colors[p] = color
            else:
                colors[p] = newcolor
                newcolor += 1

        # Add edges to the graph
        edges = []
        for ecol, ep in enumerate(row):
            if ep in nextrow:
                edges.append((ecol, nextrow.index(ep), colors[ep]))
            elif ep == rev:
                for p in dagparents:
                    edges.append((ecol, nextrow.index(p), colors[p] if len(dagparents) > 1 else color))

        # Yield and move on
        yield ((col, color), edges)
        row = nextrow
