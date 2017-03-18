# This file is part of the Stratosphere Linux IPS
# See the file 'LICENSE' for copying permission.

from colors import *
import cPickle
import math
from os import listdir
from os.path import isfile, join
import stf.common.markov_chains as mc


class Model():
    def __init__(self, id):
        self.id = id
        self.init_vector = False
        self.matrix = False
        self.self_probability = -1
        self.label = -1
        # To store when did this model had the best match. Later use to cut the state
        self.best_matching_len = -1

    def set_best_model_matching_len(self, statelen):
        self.best_matching_len = statelen

    def get_best_model_matching_len(self):
        return self.best_matching_len

    def create(self, state):
        """ Create the Markov chain itself. We use the parameter instead of the attribute so we can compute the matrix for different states """
        # Separate the letters considering the letter and the symbol as a unique state:
        # So from "88,a,b," we get: '8' '8,' 'a,' 'b,'
        try:
            # This is a first order markov model. Each individual object (letter, number, etc.) is a state
            separated_letters = list(state)
        except AttributeError:
            print_error('There is no state yet')
            return False
        # Generate the MC
        self.init_vector, self.matrix = mc.maximum_likelihood_probabilities(separated_letters, order=1)

    def compute_probability(self, state):
        """ Given a chain of letters, return the probability that it was generated by this MC """
        i = 0
        probability = 0
        penalty = -4.6  # Which is approx 0.01 probability
        # Get the initial probability of this letter in the IV.
        try:
            init_letter_prob = math.log(self.init_vector[state[i]])
        except KeyError:
            # We don't have an init_vector nor matrix, because we are still building them for each state. This is the first state
            # We assign it 0 so we don't influence the prob
            init_letter_prob = 0
        except ValueError:
            # There is not enough data to even create a matrix
            init_letter_prob = 0
        except IndexError:
            # The first letter is not in the matrix, so penalty...
            init_letter_prob = penalty
        # Assign the first letter prob
        probability = init_letter_prob
        # We should have more than 2 states at least
        while i < len(state) and len(state) > 1:
            try:
                vector = state[i] + state[i+1]
                # growing_v = state[0:i+2]
                # The transitions that include the # char will be automatically excluded
                temp_prob = self.matrix.walk_probability(vector)
                i += 1
                if temp_prob != float('-inf'):
                    probability = probability + temp_prob # logs should be summed up
                    #print_info('\tTransition [{}:{}]: {} -> Prob:{:.10f}. CumProb: {}'.format(i-1, i,vector, temp_prob, probability))
                else:
                    # Here is our trick. If two letters are not in the matrix... assign a penalty probability
                    # The temp_prob is the penalty we assign if we can't find the transition
                    probability = probability + penalty # logs should be +
                    continue
            except IndexError:
                # We are out of letters
                break
        return probability

    def set_state(self, state):
        self.state = state

    def get_state(self):
        return self.state

    def get_id(self):
        return self.id

    def set_init_vector(self, vector):
        self.init_vector = vector

    def get_init_vector(self):
        return self.init_vector

    def set_matrix(self, matrix):
        self.matrix = matrix

    def get_matrix(self):
        return self.matrix

    def set_self_probability(self, prob):
        self.self_probability = prob

    def get_self_probability(self):
        return self.self_probability

    def set_label(self, label):
        self.label = label
        protocol = label.split('-')[2]
        self.set_protocol(protocol)
        # Set the responce that should be given if matched
        if 'normal' in label.lower():
            self.matched = False
        else:
            self.matched = True

    def get_label(self):
        return self.label

    def set_protocol(self, protocol):
        self.protocol = protocol

    def get_protocol(self):
        return self.protocol

    def set_threshold(self, threshold):
        self.threshold = threshold

    def get_threshold(self):
        return self.threshold


class MarkovModelsDetection():
    """
    Class that do all the detection using markov models
    """
    def __init__(self):
        self.models = []

    def set_verbose(self, verbose):
        self.verbose = verbose

    def set_debug(self, debug):
        self.debug = debug

    def is_periodic(self,state):
        basic_patterns = ['a,a,a,','b,b,b,', 'c,c,c,', 'd,d,d,', 'e,e,e,', 'f,f,f,', 'g,g,g,', 'h,h,h,', 'i,i,i,', 'a+a+a+', 'b+b+b+', 'c+c+c+', 'd+d+d+', 'e+e+e+', 'f+f+f+', 'g+g+g+', 'h+h+h+', 'i+i+i+', 'a*a*a*', 'b*b*b*', 'c*c*c*', 'd*d*d*', 'e*e*e*', 'f*f*f*', 'g*g*g*', 'h*h*h*', 'i*i*i*', 'A,A,A,','B,B,B,', 'C,C,C,', 'D,D,D,', 'E,E,E,', 'F,F,F,', 'G,G,G,', 'H,H,H,', 'I,I,I,', 'A+A+A+', 'B+B+B+', 'C+C+C+', 'D+D+D+', 'E+E+E+', 'F+F+F+', 'G+G+G+', 'H+H+H+', 'I+I+I+', 'A*A*A*', 'B*B*B*', 'C*C*C*', 'D*D*D*', 'E*E*E*', 'F*F*F*', 'G*G*G*', 'H*H*H*', 'I*I*I*']
        for pattern in basic_patterns:
            if pattern in state:
                return True

    def set_models_folder(self, folder):
        """ Read the folder with models if specified """
        try:
            onlyfiles = [f for f in listdir(folder) if isfile(join(folder, f))]
            for file in onlyfiles:
                self.set_model_to_detect(join(folder, file))
            return True
        except OSError:
            print 'Inexistent directory for folders.'
            return False

    def set_model_to_detect(self, file):
        """
        Receives a file and extracts the model in it
        """
        input = open(file, 'r')
        try:
            id = self.models[-1].get_id() + 1
        except (KeyError, IndexError):
            id = 1
        model = Model(id)
        model.set_init_vector(cPickle.load(input))
        model.set_matrix(cPickle.load(input))
        model.set_state(cPickle.load(input))
        model.set_self_probability(cPickle.load(input))
        model.set_label(cPickle.load(input))
        model.set_threshold(cPickle.load(input))
        self.models.append(model)
        if self.verbose > 2:
            print '\tAdding model {} to the list.'.format(model.get_label())
        input.close()

    def detect(self, tuple, verbose, debug):
        """
        Main detect function
        """
        try:
            # Clear the temp best model
            best_model_so_far = False
            best_distance_so_far = float('inf')
            # best_model_matching_len = -1
            # Set the verbose and debug
            self.verbose = verbose
            self.debug = debug
            # Only detect states with more than 3 letters
            if len(tuple.get_state()) < 4:
                if self.debug > 3:
                    print '\t-> State too small'
                return (False, False, False)
            # Use the current models for detection
            for model in self.models:
                # Only detect if protocol matches
                if model.get_protocol().lower() != tuple.get_protocol().lower():
                    # Go get the next
                    continue
                # Letters of the trained model. Get from the last detected letter to the end. NO CUT HERE. We dont cut the training letters, because if we do, we have to cut ALL of them,
                # including the matching and the not matching ones.
                train_sequence = model.get_state()[0:len(tuple.get_state())]
                # Recreate the matrix so far
                model.create(train_sequence)
                # Get the new original prob so far...
                training_original_prob = model.compute_probability(train_sequence)
                # Now obtain the probability for testing. The prob is computed by using the API on the train model, which knows its own matrix
                test_prob = model.compute_probability(tuple.get_state())
                # Get the distance
                prob_distance = -1
                if training_original_prob != -1 and test_prob != -1 and training_original_prob <= test_prob:
                    try:
                        prob_distance = training_original_prob / test_prob
                    except ZeroDivisionError:
                        prob_distance = -1
                elif training_original_prob != -1 and test_prob != -1 and training_original_prob > test_prob:
                    try:
                        prob_distance = test_prob / training_original_prob
                    except ZeroDivisionError:
                        prob_distance = -1
                if self.debug > 2:
                    print '\t\tTrained Model: {}. Label: {}. Threshold: {}, State: {}'.format(model.get_id(), model.get_label(), model.get_threshold(), train_sequence)
                    print '\t\t\tTest Model: {}. State: {}'.format(tuple.get_id(), tuple.get_state())
                    print '\t\t\tTrain prob: {}'.format(training_original_prob)
                    print '\t\t\tTest prob: {}'.format(test_prob)
                    print '\t\t\tDistance: {}'.format(prob_distance)
                    if self.debug > 4:
                        print '\t\t\tTrained Matrix:'
                        matrix = model.get_matrix()
                        for i in matrix:
                            print '\t\t\t\t{}:{}'.format(i, matrix[i])
                # If we matched and we are the best so far
                if prob_distance >= 1 and prob_distance <= model.get_threshold() and prob_distance < best_distance_so_far:
                    # Store for this model, where it had its match. Len of the state. So later we can cut the state.
                    model.set_best_model_matching_len(len(tuple.get_state()))
                    # Now store the best
                    best_model_so_far = model
                    best_distance_so_far = prob_distance
                    if self.debug > 3:
                        print '\t\t\t\tThis model is the best so far. State len: {}'.format(len(tuple.get_state()))
                    # New decision. If one model matched, just stop checking the rest of the models
                    break
            # If we detected something
            if best_model_so_far:
                return (best_model_so_far.matched, best_model_so_far.get_label(), best_model_so_far.get_best_model_matching_len())
            else:
                return (False, False, False)
        except Exception as inst:
            print 'Problem in detect() in markov_models_1'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(-1)



__markov_models__ = MarkovModelsDetection()
