Naive Bayesian Classifier
=========================
This is an implementation of a Naive Bayesian Classifier written in Python. The utility uses statistical methods to classify documents, based on the words that appear within them. A common application for this type of software is in email spam filters.

The utility must first be 'trained' using large numbers of pre-classified documents, during the training phase a database is populated with information about how often certain words appear in each type of document. Once training is complete, unclassified documents can be submitted to the classifier which will return a value between 0 and 1, indicating the probablity that the document belongs to one class of document rather than another.

Training
--------

To train the utility, use the following command:

    python bayes.py learn <doctype> <file> <count>

+ The *doctype* argument can be any non-empty value - this is just the name you have chosen for the type of document that you are showing to the classifier
+ The *file* argument indicates the location of the file containing the training data that you wish to use
+ The *count* argument is a numeric value indicating the number of separate documents contained in the training data file

For example:

    python bayes.py learn spam all_my_spam.txt 10000
    python bayes.py learn ham inbox.txt 10000

Classification
--------------

Once training is complete, classification is performed using this command:

    bayes.py classify <file> <doctype> <doctype>

+ The *file* argument indicates the location of the file containing the document to be classified
+ The two *doctype* arguments are the names of the document types against which the input file will be compared

For example:

    python bayes.py classify nigerian_finance_email.txt spam ham
    > Probability that document is spam rather than ham is 0.98