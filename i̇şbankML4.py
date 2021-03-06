# -*- coding: utf-8 -*-
"""İşBank4.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1pZfi-IqAGy5qDGW_g4-BhEsftGom0pUR

#İş Bankası Machine Learning Challange #4

### Kaggle Requirements
"""

!pip install -q kaggle
from google.colab import files
files.upload()

!mkdir ~/.kaggle
!cp kaggle.json ~/.kaggle/
!chmod 600 ~/.kaggle/kaggle.json
!kaggle competitions download -c turkiye-is-bankasi-machine-learning-challenge-4
!unzip train.csv.zip -d sample_data
!unzip test.csv.zip -d sample_data
!unzip sample_submission.csv.zip -d sample_data

"""### Importing Libraries"""

# Metrics and preprocessing
from sklearn.model_selection import train_test_split
from sklearn.model_selection import KFold
from sklearn.metrics import roc_auc_score
from imblearn.over_sampling import ADASYN
from sklearn.metrics import f1_score
from sklearn import metrics
import sklearn

import pandas as pd 
import numpy as np
import seaborn as sns


#models
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
import lightgbm as lgb
import xgboost as xgb


#hypertunning
from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import StratifiedKFold

"""# DATA PREPROCEESING"""

df_train = pd.read_csv("sample_data/train.csv")
df_train.shape

df_test = pd.read_csv("sample_data/test.csv")
df_test.shape

df_test.drop("ID",inplace = True,axis = 1)

Y = df_train.iloc[:, 0]
df_train.drop("TARGET",inplace =True,axis =1)

columns = ['TXN_TRM', 'CST_NR','CC_NR']

df_train.drop(columns, inplace=True, axis=1)
df_train.head()

df_test.drop(columns, inplace=True, axis=1)
df_test.head()

frames = [df_train,df_test]
result = pd.concat(frames,ignore_index=True)

result['TXN_SOURCE'] = pd.factorize(result.TXN_SOURCE)[0]
result['TXN_ENTRY'] = pd.factorize(result.TXN_ENTRY)[0]
result['CITY'] = pd.factorize(result.CITY)[0]
result['COUNTRY'] = pd.factorize(result.COUNTRY)[0]
result['MC_NAME'] = pd.factorize(result.MC_NAME)[0]
result['MC_ID'] = pd.factorize(result.MC_ID)[0]
result['MCC_CODE'] = pd.factorize(result.MCC_CODE)[0]

train = result.iloc[:607507,:]
test = result.iloc[607507:,:]

X = train.loc[:, train.columns != 'TARGET']

"""### Adaptive Synthetic Sampling"""

X_adasyn, y_adasyn = ADASYN().fit_resample(X, Y)

"""# MODEL TRAINING"""

X_train, X_test, y_train, y_test = train_test_split(X_adasyn, y_adasyn, test_size=0.2, random_state=40, stratify=y_adasyn)

"""## LGBM"""

lgb_model = lgb.LGBMClassifier()

n_estimators = range(50, 200, 50)
param_grid = dict(n_estimators=n_estimators)

max_depth = range(5, 20, 5)
param_grid['max_depth'] = max_depth
print(param_grid)

kfold = StratifiedKFold(n_splits=3, shuffle=True, random_state=7)
grid_search = GridSearchCV(lgb_model, param_grid, scoring="roc_auc", n_jobs=-1, cv=kfold,verbose = 3)
grid_result = grid_search.fit(X_train,y_train)

# summarize results
print("Best: %f using %s" % (grid_result.best_score_, grid_result.best_params_))
grid_result.best_params_

y_pred = grid_result.best_estimator_.predict(X_test)

print("hypertunned LGBM with all columns as features")
print("F1 score is {}".format(f1_score(y_test, y_pred)))
fpr, tpr, thresholds = metrics.roc_curve(y_test, y_pred)
print("AUC is {}".format(metrics.auc(fpr, tpr)))
print("Recall is {}".format(metrics.recall_score(y_test, y_pred)))
print("Precision is {}".format(metrics.precision_score(y_test, y_pred)))

"""## LGBM Optuna

"""

!pip install optuna

import optuna

def objective(trial):
    X_train, X_test, y_train, y_test = train_test_split(X_adasyn, y_adasyn, test_size=0.2, random_state=40, stratify=y_adasyn)
    dtrain = lgb.Dataset(X_train, label=y_train)

    param = {
        "objective": "binary",
        "metric": "binary_logloss",
        "verbosity": -1,
        "boosting_type": "gbdt",
        "lambda_l1": trial.suggest_float("lambda_l1", 1e-8, 10.0, log=True),
        "lambda_l2": trial.suggest_float("lambda_l2", 1e-8, 10.0, log=True),
        "num_leaves": trial.suggest_int("num_leaves", 2, 256),
        "feature_fraction": trial.suggest_float("feature_fraction", 0.4, 1.0),
        "bagging_fraction": trial.suggest_float("bagging_fraction", 0.4, 1.0),
        "bagging_freq": trial.suggest_int("bagging_freq", 1, 7),
        "min_child_samples": trial.suggest_int("min_child_samples", 5, 100),
    }

    gbm = lgb.train(param, dtrain)
    preds = gbm.predict(X_test)
    pred_labels = np.rint(preds)
    accuracy = sklearn.metrics.accuracy_score(y_test, pred_labels)
    return accuracy

study = optuna.create_study(direction="maximize")
study.optimize(objective, n_trials=100)

print("Number of finished trials: {}".format(len(study.trials)))

print("Best trial:")
trial = study.best_trial

print("  Value: {}".format(trial.value))

print("  Params: ")
for key, value in trial.params.items():
    print("    {}: {}".format(key, value))

lgb_model = lgb.LGBMClassifier(lambda_l1= 2.6253396719072427e-06,
    lambda_l2= 1.9167201660099258e-08,
    num_levels= 251,
    feature_fraction= 0.999344921308945,
    bagging_fraction=0.918156018901188,
    bagging_freq= 5,
    min_child_samples= 14)

preds = lgb_model.predict(X_test)

"""### Submission"""

df_submission = pd.read_csv("sample_data/sample_submission.csv")
df_submission.head()

submission = grid_result.best_estimator_.predict_proba(test)

fraud_prob = submission[:,1]

df_submission.drop('Predicted', axis=1, inplace=True)
df_submission['Predicted'] = fraud_prob
df_submission.to_csv('sublgbm2.csv',encoding='utf-8',index= False)