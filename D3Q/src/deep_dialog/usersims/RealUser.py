import argparse, json, random, copy
from deep_dialog.usersims import UserSimulator
from deep_dialog import dialog_config

class RealUser(UserSimulator):

    def __init__(self, movie_dict=None, act_set=None, slot_set=None, start_set=None, params=None):
        """ Constructor shared by all user simulators """

        self.movie_dict = movie_dict
        self.act_set = act_set
        self.slot_set = slot_set
        self.start_set = start_set

        self.max_turn = params['max_turn']
        self.slot_err_probability = params['slot_err_probability']
        self.slot_err_mode = params['slot_err_mode']
        self.intent_err_probability = params['intent_err_probability']

        self.simulator_run_mode = params['simulator_run_mode']
        self.simulator_act_level = params['simulator_act_level']
        self.user_input_mode = 0

        self.learning_phase = params['learning_phase']

    def initialize_episode(self):
        """ Initialize a new episode (dialog)
        state['history_slots']: keeps all the informed_slots
        state['rest_slots']: keep all the slots (which is still in the stack yet)
        """

        self.state = {}
        self.state['history_slots'] = {}
        self.state['inform_slots'] = {}
        self.state['request_slots'] = {}
        self.state['rest_slots'] = []
        self.state['turn'] = 0

        self.episode_over = False
        self.dialog_status = dialog_config.NO_OUTCOME_YET

        # self.goal =  random.choice(self.start_set)
        # self.goal = self._sample_goal()
        # self.goal['request_slots']['ticket'] = 'UNK'
        self.constraint_check = dialog_config.CONSTRAINT_CHECK_FAILURE
        user_action = self.get_user_action_from_cmd()

        self.state['diaact'] = user_action['diaact']
        if (self.state['diaact'] in ['thanks','closing']): self.episode_over = True #episode_over = True
        else: self.episode_over = False

        user_action['turn'] = 0
        self.state['inform_slots'] = user_action['inform_slots']
        self.state['request_slots'] = user_action['request_slots']
        self.state['rest_slots'] = []
        assert (self.episode_over != 1, ' but we just started')
        return user_action

    def get_user_action_from_cmd(self):
        """   """
        command = input()
        if self.user_input_mode == 0:  # nl
            user_action = self.generate_diaact_from_nl(command)

        return user_action

    def generate_diaact_from_nl(self, string):
        """ Generate Dia_Act Form with NLU """

        user_action = {}
        user_action['diaact'] = 'UNK'
        user_action['inform_slots'] = {}
        user_action['request_slots'] = {}

        if len(string) > 0:
            user_action = self.nlu_model.generate_dia_act(string)

        user_action['nl'] = string
        return user_action

    def corrupt(self, user_action):
        """ Randomly corrupt an action with error probs (slot_err_probability and slot_err_mode) on Slot and Intent (intent_err_probability). """

        for slot in user_action['inform_slots'].keys():
            slot_err_prob_sample = random.random()
            if slot_err_prob_sample < self.slot_err_probability:  # add noise for slot level
                if self.slot_err_mode == 0:  # replace the slot_value only
                    if slot in self.movie_dict.keys(): user_action['inform_slots'][slot] = random.choice(
                        self.movie_dict[slot])
                elif self.slot_err_mode == 1:  # combined
                    slot_err_random = random.random()
                    if slot_err_random <= 0.33:
                        if slot in self.movie_dict.keys(): user_action['inform_slots'][slot] = random.choice(
                            self.movie_dict[slot])
                    elif slot_err_random > 0.33 and slot_err_random <= 0.66:
                        del user_action['inform_slots'][slot]
                        random_slot = random.choice(self.movie_dict.keys())
                        user_action[random_slot] = random.choice(self.movie_dict[random_slot])
                    else:
                        del user_action['inform_slots'][slot]
                elif self.slot_err_mode == 2:  # replace slot and its values
                    del user_action['inform_slots'][slot]
                    random_slot = random.choice(self.movie_dict.keys())
                    user_action[random_slot] = random.choice(self.movie_dict[random_slot])
                elif self.slot_err_mode == 3:  # delete the slot
                    del user_action['inform_slots'][slot]

        intent_err_sample = random.random()
        if intent_err_sample < self.intent_err_probability:  # add noise for intent level
            user_action['diaact'] = random.choice(list(self.act_set.keys()))

    def debug_falk_goal(self):
        """ Debug function: build a fake goal mannually (Can be moved in future) """

        self.goal['inform_slots'].clear()
        # self.goal['inform_slots']['city'] = 'seattle'
        self.goal['inform_slots']['numberofpeople'] = '2'
        # self.goal['inform_slots']['theater'] = 'amc pacific place 11 theater'
        # self.goal['inform_slots']['starttime'] = '10:00 pm'
        # self.goal['inform_slots']['date'] = 'tomorrow'
        self.goal['inform_slots']['moviename'] = 'zoology'
        self.goal['inform_slots']['distanceconstraints'] = 'close to 95833'
        self.goal['request_slots'].clear()
        self.goal['request_slots']['ticket'] = 'UNK'
        self.goal['request_slots']['theater'] = 'UNK'
        self.goal['request_slots']['starttime'] = 'UNK'
        self.goal['request_slots']['date'] = 'UNK'

    def next(self, system_action):
        """ Generate next User Action based on last System Action """
        self.state['turn'] += 2
        self.episode_over = False
        self.dialog_status = dialog_config.NO_OUTCOME_YET

        sys_act = system_action['diaact']

        if (self.max_turn > 0 and self.state['turn'] > self.max_turn):
            self.dialog_status = dialog_config.FAILED_DIALOG
            self.episode_over = True
            self.state['diaact'] = "closing"
        else:
            self.state['history_slots'].update(self.state['inform_slots'])
            self.state['inform_slots'].clear()

            if sys_act == "inform":
                self.response_inform(system_action)
            elif sys_act == "multiple_choice":
                self.response_multiple_choice(system_action)
            elif sys_act == "request":
                self.response_request(system_action)
            elif sys_act == "thanks":
                self.response_thanks(system_action)
            elif sys_act == "confirm_answer":
                self.response_confirm_answer(system_action)
            elif sys_act == "closing":
                self.episode_over = True
                self.state['diaact'] = "thanks"

        # self.corrupt(self.state)

        response_action = {}
        response_action['diaact'] = self.state['diaact']
        response_action['inform_slots'] = self.state['inform_slots']
        response_action['request_slots'] = self.state['request_slots']
        response_action['turn'] = self.state['turn']
        response_action['nl'] = self.state['nl']

        # add NL to dia_act
        # self.add_nl_to_action(response_action)
        return response_action, self.episode_over, self.dialog_status

    def get_state_for_user(self, system_action):
        """ Get the state representatons to send to agent """
        # state = {'user_action': self.history_dictionaries[-1], 'current_slots': self.current_slots, 'kb_results': self.kb_results_for_state()}
        state = {'user_action': self.history_dictionaries[-1], 'current_slots': self.current_slots,
                 # 'kb_results': self.kb_results_for_state(),
                 'kb_results_dict': self.kb_helper.database_results_for_agent(self.current_slots),
                 'turn': self.turn_count, 'history': self.history_dictionaries,
                 'agent_action': self.history_dictionaries[-2] if len(self.history_dictionaries) > 1 else None}
        return copy.deepcopy(state)

    def response_confirm_answer(self, system_action):
        """ Response for Confirm_Answer (System Action) """

        if len(self.state['rest_slots']) > 0:
            request_slot = random.choice(self.state['rest_slots'])

            if request_slot in self.goal['request_slots'].keys():
                self.state['diaact'] = "request"
                self.state['request_slots'][request_slot] = "UNK"
            elif request_slot in self.goal['inform_slots'].keys():
                self.state['diaact'] = "inform"
                self.state['inform_slots'][request_slot] = self.goal['inform_slots'][request_slot]
                if request_slot in self.state['rest_slots']:
                    self.state['rest_slots'].remove(request_slot)
        else:
            self.state['diaact'] = "thanks"

    def response_thanks(self, system_action):
        """ Response for Thanks (System Action) """

        self.episode_over = True
        self.dialog_status = dialog_config.SUCCESS_DIALOG

        request_slot_set = copy.deepcopy(list(self.state['request_slots'].keys()))
        if 'ticket' in request_slot_set:
            request_slot_set.remove('ticket')
        rest_slot_set = copy.deepcopy(self.state['rest_slots'])
        if 'ticket' in rest_slot_set:
            rest_slot_set.remove('ticket')

        if len(request_slot_set) > 0 or len(rest_slot_set) > 0:
            self.dialog_status = dialog_config.FAILED_DIALOG

        for info_slot in self.state['history_slots'].keys():
            if self.state['history_slots'][info_slot] == dialog_config.NO_VALUE_MATCH:
                self.dialog_status = dialog_config.FAILED_DIALOG

        if 'ticket' in system_action['inform_slots'].keys():
            if system_action['inform_slots']['ticket'] == dialog_config.NO_VALUE_MATCH:
                self.dialog_status = dialog_config.FAILED_DIALOG

        if self.constraint_check == dialog_config.CONSTRAINT_CHECK_FAILURE:
            self.dialog_status = dialog_config.FAILED_DIALOG

    def response_request(self, system_action):
        """ Response for Request (System Action) """
        user_action = self.get_user_action_from_cmd()
        for slot in user_action['request_slots'].keys():
            self.state['request_slots'][slot] = user_action['request_slots'][slot]
        for slot in user_action['inform_slots'].keys():
            self.state['inform_slots'][slot] = user_action['inform_slots'][slot]
        self.state['diaact'] = user_action['diaact']
        self.state['nl'] = user_action['nl']

        # if len(system_action['request_slots'].keys()) > 0:
        #     slot = list(system_action['request_slots'].keys())[0]  # only one slot
        #     if slot in self.goal['inform_slots'].keys():  # request slot in user's constraints  #and slot not in self.state['request_slots'].keys():
        #         self.state['inform_slots'][slot] = self.goal['inform_slots'][slot]
        #         self.state['diaact'] = "inform"
        #         if slot in self.state['rest_slots']: self.state['rest_slots'].remove(slot)
        #         if slot in self.state['request_slots'].keys(): del self.state['request_slots'][slot]
        #         self.state['request_slots'].clear()
        #     elif slot in self.goal['request_slots'].keys() and slot not in self.state['rest_slots'] and slot in \
        #             self.state['history_slots'].keys():  # the requested slot has been answered
        #         self.state['inform_slots'][slot] = self.state['history_slots'][slot]
        #         self.state['request_slots'].clear()
        #         self.state['diaact'] = "inform"
        #     elif slot in self.goal['request_slots'].keys() and slot in self.state[
        #         'rest_slots']:  # request slot in user's goal's request slots, and not answered yet
        #         self.state['diaact'] = "request"  # "confirm_question"
        #         self.state['request_slots'][slot] = "UNK"
        #
        #
        #         ########################################################################
        #         # Inform the rest of informable slots
        #         ########################################################################
        #         for info_slot in self.state['rest_slots']:
        #             if info_slot in self.goal['inform_slots'].keys():
        #                 self.state['inform_slots'][info_slot] = self.goal['inform_slots'][info_slot]
        #
        #         for info_slot in self.state['inform_slots'].keys():
        #             if info_slot in self.state['rest_slots']:
        #                 self.state['rest_slots'].remove(info_slot)
        #     else:
        #         if len(self.state['request_slots']) == 0 and len(self.state['rest_slots']) == 0:
        #             self.state['diaact'] = "thanks"
        #         else:
        #             self.state['diaact'] = "inform"
        #         self.state['inform_slots'][slot] = dialog_config.I_DO_NOT_CARE

    def response_multiple_choice(self, system_action):
        """ Response for Multiple_Choice (System Action) """

        slot = system_action['inform_slots'].keys()[0]
        if slot in self.goal['inform_slots'].keys():
            self.state['inform_slots'][slot] = self.goal['inform_slots'][slot]
        elif slot in self.goal['request_slots'].keys():
            self.state['inform_slots'][slot] = random.choice(system_action['inform_slots'][slot])

        self.state['diaact'] = "inform"
        if slot in self.state['rest_slots']: self.state['rest_slots'].remove(slot)
        if slot in self.state['request_slots'].keys(): del self.state['request_slots'][slot]

    def response_inform(self, system_action):
        """ Response for Inform (System Action) """

        if 'taskcomplete' in system_action[
            'inform_slots'].keys():  # check all the constraints from agents with user goal
            self.state['diaact'] = "thanks"
            # if 'ticket' in self.state['rest_slots']: self.state['request_slots']['ticket'] = 'UNK'
            self.constraint_check = dialog_config.CONSTRAINT_CHECK_SUCCESS

            if system_action['inform_slots']['taskcomplete'] == dialog_config.NO_VALUE_MATCH:
                self.state['history_slots']['ticket'] = dialog_config.NO_VALUE_MATCH
                if 'ticket' in self.state['rest_slots']: self.state['rest_slots'].remove('ticket')
                if 'ticket' in self.state['request_slots'].keys(): del self.state['request_slots']['ticket']

        else:
            for slot in system_action['inform_slots'].keys():
                self.state['history_slots'][slot] = system_action['inform_slots'][slot]

        user_action = self.get_user_action_from_cmd()
        for slot in user_action['request_slots'].keys():
            self.state['request_slots'][slot] = user_action['request_slots'][slot]
        for slot in user_action['inform_slots'].keys():
            self.state['inform_slots'][slot] = user_action['inform_slots'][slot]
        self.state['diaact'] = user_action['diaact']
        self.state['nl'] = user_action['nl']

    def state_to_action(self, state):
        """ Generate an action by getting input interactively from the command line """

        user_action = state['user_action']
        # get input from the command line
        print("Turn", user_action['turn'] + 1, "usr:", )
        command = input()

        if self.user_input_mode == 0:  # nl
            act_slot_value_response = self.generate_diaact_from_nl(command)
        elif self.agent_input_mode == 1:  # dia_act
            act_slot_value_response = self.parse_str_to_diaact(command)

        return {"act_slot_response": act_slot_value_response, "act_slot_value_response": act_slot_value_response}

def main(params):
    user_sim = RealUser()
    user_sim.initialize_episode()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    args = parser.parse_args()
    params = vars(args)

    print("User Simulator Parameters:")
    print(json.dumps(params, indent=2))

    main(params)

