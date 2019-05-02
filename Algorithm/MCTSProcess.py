from copy import deepcopy

"""
State object must implement the following functions: 
- assign(resource_index, incident)
- get_resource(resource_index)
- update(time)
- determine_resources_in_range(incident, dispatch_factor, time)
- get_next_available_resource_time()
- get_resp_time(resource_index) ***
- get_resource_location(resource_index) ***
- determine_closest_resource(incident, time)


incident objects should have the following member values: 
- time
- location

"""


class TreeNode:
    def __init__(self, state,
                 orig_decision=None,
                 depth=0,
                 running_cost=0,
                 name='root',
                 children=None,
                 parent=None,
                 assigned_incident=None,
                 assigned_resource_index=None,
                 this_node_cost=None,
                 assigned_resource_location=None):

        self.depth = depth
        self.state = state
        self.running_cost = running_cost
        self.orig_decision = orig_decision
        self.parent = parent
        self.assigned_incident = assigned_incident
        self.assigned_resource_index = assigned_resource_index
        self.this_node_cost = this_node_cost
        self.assigned_resource_location = assigned_resource_location

        self.children = []
        if children is not None:
            for child in children:
                self.add_child(child)

        self.name = name

    def __repr__(self):
        return self.name

    def add_child(self, node):
        assert isinstance(node, TreeNode)
        self.children.append(node)


class MCTSProcess:
    def __init__(self, look_ahead_horizon, discount_factor, branch_depth, dispatch_factor):
        self.look_ahead_horizon = look_ahead_horizon
        self.discount_factor = discount_factor
        self.branch_depth = branch_depth
        self.dispatch_factor = dispatch_factor

        self.leaf_stack = None
        self.start_time = None
        self.end_time = None
        self.predicted_incident_chain = None
        self.leaf_stack = None

    def mcts_search(self, root_state, predicted_incident_chain,
                    decision_incident, possible_dispatch_resource_indices):

        tree = TreeNode(deepcopy(root_state))
        final_leaves = []
        self.leaf_stack = []
        self.predicted_incident_chain = predicted_incident_chain

        self.start_time = decision_incident.time
        self.end_time = self.start_time + self.look_ahead_horizon

        for resource_index in possible_dispatch_resource_indices:
            new_state = deepcopy(tree.state)
            new_state.assign(resource_index, decision_incident, )
            resp_time = new_state.get_resp_time(resource_index)
            updated_cost = self.resp_cost(tree.running_cost, resp_time, tree.depth, 0)

            m_orig_dec = resource_index

            child = TreeNode(state=new_state,
                             orig_decision=m_orig_dec,
                             depth=tree.depth + 1,
                             running_cost=updated_cost,
                             parent=tree,
                             assigned_incident=decision_incident,
                             assigned_resource_index=resource_index,
                             this_node_cost=resp_time,
                             assigned_resource_location=new_state.get_location(resource_index))
            tree.add_child(child)
            self.leaf_stack.append(child)

        while len(self.leaf_stack) > 0:
            current_leaf = self.leaf_stack.pop(len(self.leaf_stack) - 1)

            if len(self.predicted_incident_chain) >= current_leaf.depth:
                current_predicted_incident = self.predicted_incident_chain[current_leaf.depth - 1]
                curr_time = current_predicted_incident.time + self.start_time

                if curr_time < self.end_time:  # else end and put the current leaf in the final leaves

                    current_leaf.state.update(curr_time, )
                    closest_resp_index, cloesest_responder, closest_arr = current_leaf.state.determine_closest_resource(
                        current_predicted_incident,
                        curr_time,
                        True)

                    if closest_resp_index is None:

                        self.queue_for_waiting_incidents(current_predicted_incident, curr_time, current_leaf)

                    else:
                        if current_leaf.depth <= self.branch_depth:
                            poss_resources = current_leaf.state.determine_resources_in_range(current_predicted_incident,
                                                                                             self.dispatch_factor,
                                                                                             curr_time,
                                                                                             False)
                            for resource_index in poss_resources:
                                child = self.create_new_child_sim(current_leaf,
                                                                  resource_index,
                                                                  current_predicted_incident,
                                                                  curr_time)
                                current_leaf.add_child(child)
                                self.leaf_stack.append(child)

                        else:
                            resource_index = current_leaf.state.determine_closest_resource(current_predicted_incident,
                                                                                           curr_time,
                                                                                           False)[0]
                            child = self.create_new_child_sim(current_leaf,
                                                              resource_index,
                                                              current_predicted_incident,
                                                              curr_time)
                            current_leaf.add_child(child)
                            self.leaf_stack.append(child)

                else:
                    final_leaves.append(current_leaf)

            else:
                final_leaves.append(current_leaf)

        # Return dict of best score for each resource
        best_scores = {}

        for leaf in final_leaves:
            orig = leaf.orig_decision
            if orig in best_scores:
                if leaf.running_cost < best_scores[orig]:
                    best_scores[orig] = leaf.running_cost
            else:
                best_scores[orig] = leaf.running_cost

        return best_scores, tree

    def queue_for_waiting_incidents(self, current_incident, curr_time, current_leaf):

        incident_queue = list()
        incident_queue.append(current_incident)
        queue_time = curr_time
        current_incident_depth = current_leaf.depth
        first = True

        while len(incident_queue) > 0 \
                and queue_time < self.end_time \
                and current_incident_depth - 1 < len(self.predicted_incident_chain):

            if first:
                first = False
            else:
                incident_queue.append(self.predicted_incident_chain[current_incident_depth - 1])

            if current_incident_depth < len(self.predicted_incident_chain):
                next_incident_time = self.predicted_incident_chain[current_incident_depth].time
                next_available_time = current_leaf.state.get_next_available_resource_time()

                while queue_time + next_available_time + 1 < queue_time + next_incident_time \
                        and len(incident_queue) > 0:

                    queue_time, incident_queue, current_leaf, child, next_available_time = \
                        self.update_queue_simulation_chain(queue_time,
                                                           next_available_time,
                                                           incident_queue,
                                                           current_leaf)

                    if len(incident_queue) < 1 \
                            or queue_time + next_available_time + 1 < queue_time + next_incident_time:
                        self.leaf_stack.append(child)
                    else:
                        current_leaf = child
            else:
                next_available_time = current_leaf.state.get_next_available_resource_time()
                while len(incident_queue) > 0:
                    queue_time, incident_queue, current_leaf, child, next_available_time = \
                        self.update_queue_simulation_chain(queue_time,
                                                           next_available_time,
                                                           incident_queue,
                                                           current_leaf)

                    current_leaf = child

                self.leaf_stack.append(current_leaf)

            current_incident_depth += 1

    def resp_cost(self, current_cost,
                  new_cost,
                  depth,
                  time_difference_from_beginning_in_secs):

        minutes = time_difference_from_beginning_in_secs / 60
        if minutes < 1.0:
            minutes = 1.0

        cost = current_cost + ((new_cost - current_cost) / (depth + 1)) * (self.discount_factor ** minutes)
        return cost

    def create_new_child_sim(self, current_leaf, resource_index, curr_incident,
                             curr_time):
        new_state = deepcopy(current_leaf.state)
        new_state.assign(resource_index, curr_incident)
        resp_time = new_state.get_resp_time(resource_index)

        updated_cost = self.resp_cost(current_leaf.running_cost, resp_time,
                                      current_leaf.depth, curr_time - self.start_time)

        if current_leaf.orig_decision is None:
            original_decision_in_subtree = resource_index
        else:
            original_decision_in_subtree = current_leaf.orig_decision

        child = TreeNode(state=new_state,
                         orig_decision=original_decision_in_subtree,
                         depth=current_leaf.depth + 1,
                         running_cost=updated_cost,
                         parent=current_leaf,
                         assigned_incident=curr_incident,
                         assigned_resource_index=resource_index,
                         this_node_cost=resp_time,
                         assigned_resource_location=new_state.get_location(resource_index))
        return child

    def update_queue_simulation_chain(self, queue_time, next_available_time,
                                      incident_queue, current_leaf):

        queue_time += next_available_time + 1
        incident = incident_queue.pop(0)
        new_state = deepcopy(current_leaf.state)
        new_state.update(queue_time, )

        possible_resources = new_state.determine_resources_in_range(incident,
                                                                    self.dispatch_factor,
                                                                    queue_time,
                                                                    False)
        new_state.assign(possible_resources[0], incident)
        response_time = new_state.get_resp_time(possible_resources[0])
        updated_cost = self.resp_cost(current_leaf.running_cost, response_time,
                                      current_leaf.depth, queue_time - self.start_time)

        if current_leaf.orig_decision is None:
            original_action_taken_in_subtree = possible_resources[0]
        else:
            original_action_taken_in_subtree = current_leaf.orig_decision

        child = TreeNode(state=new_state,
                         orig_decision=original_action_taken_in_subtree,
                         depth=current_leaf.depth + 1,
                         running_cost=updated_cost,
                         parent=current_leaf,
                         assigned_incident=incident,
                         assigned_resource_index=possible_resources[0],
                         this_node_cost=response_time,
                         assigned_resource_location=new_state.get_location(possible_resources[0]))
        current_leaf.add_child(child)

        next_available_time = child.state.get_next_available_resource_time()

        return queue_time, incident_queue, current_leaf, child, next_available_time
