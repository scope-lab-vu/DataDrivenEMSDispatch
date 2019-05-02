# Integrated Safety Incident Forecasting Analysis and Emergency Resources Dispatch Optimization

The objective of this research is to understand and improve the resource coordination and dispatch mechanisms used by first responders in smart and connected communities. In prior art, as well as practice, incident forecasting and response are typically siloed by category and department, reducing effectiveness of prediction and precluding efficient coordination of resources. This research project funded from a grant by National Science Foundation has provided us the capability to study and develop algorithms for  integrating both the data and emergency resources from distinct urban agencies in the City of Nashville along with other widely available data such as pedestrian traffic, road characteristics, traffic congestion, and weather. Our results include models for anticipating heterogeneous incidents such as distinct categories of crime, as well as vehicular accidents.  With these models we have also developed decision support tools to optimize both resource  allocation and response times. These tools will help the emergency responders determine which units to dispatch (police, fire, or both) in order to minimize expected response time, and what equipment is most appropriate, taking into account the time, location, and nature of incidents, as well as those predicted to occur in the future. Ultimately, the methods developed in this research can be applied to other domains where multi-resource spatio-temporal scheduling is a challenge.

## Acknowledgements

This work is sponsored by the National Science Foundation under award numbers CNS1640624 and IIS1814958.  We also thank our partners from Metro Nashville Fire Department and Metro Nashville Information Technology Services in this work.

## Disclaimer
This project, including the code and documentation, is a work in progress. The code is available for use under the MIT license, but we do not guarantee support. 


*instilation instructions pending*

## File Structure
The Algorithms folder contains code for making dispatching decisions, [which is described in detail in our white paper](http://www.isis.vanderbilt.edu/sites/default/files/ICCPS_CameraReady_2019_arxiv.pdf). The Dashboard folder contains the visualization dashboard, which is described by the usage guide below. 

NFD DASHBOARD TOOL USAGE GUIDE

 
[Youtube Video Demonstration](https://www.youtube.com/watch?v=HDNpg4Q3CZw)

Note - This document is intended as a guide for the end-user, and not a
technical guide to the setup or the algorithmic background for the tool.
In case you have issues, please contact the team at Vanderbilt for help.

Key Contributors: 

1.  Abhishek Dubey

2.  Yevgeniy Vorobeychik

3.  Gautam Biswas

Students --

1.  Zilin Wang

2.  Ayan Mukhopadhyay

3.  Geoffrey Pettet

4.  Fangzhou Sun

Table of Contents {#table-of-contents .TOCHeading}
=================

[Modes 4](#modes)

[Background Jobs 4](#background-jobs)

[Modes - description 5](#modes---description)

[Historical Mode 5](#historical-mode)

[Prediction Mode 7](#prediction-mode)

[Explore Mode 8](#explore-mode)

[Dispatch Mode 10](#dispatch-mode)

[Background Jobs - description 12](#background-jobs---description)

[Data Ingestion 12](#data-ingestion)

[Prediction Model Upgrade 12](#prediction-model-upgrade)

[Overall Monitoring 13](#overall-monitoring)

The NFD Dashboard tool is a means to visualize historical data,
summarize statistics from data, predict future incidents, explore the
impact of adding fire stations on response times and get real-time
guidance on dispatch decisions. This document is a one-stop guide for
the entire tool, and is meant to be used by the end user.

Modes
=====

The tool has four basic modes, with the following capabilities --

-   Historical -- The mode enables user to visualize historical data as
    heat map/ incident scatter plots on a geographical map of Nashville.

-   Prediction -- Enables the user to predict incidents for arbitrary
    future dates according the incident type.

-   Explore -- Lets the user add a new fire station,

-   Recommend -- Lets the user calculate a new station's effect on the
    response time.

-   Dispatch -- Helps the user in plotting pending incidents that need
    to be serviced, and provides a recommended dispatch decision.

Background Jobs
===============

The tool has three primary background jobs -- data ingestion to the
mongoDB used by the dashboard, upgrade of the prediction algorithm with
streaming data and overall monitoring of the tool. We discuss the modes
as well as the jobs individually in this document.

Modes - description 
====================

Historical Mode
---------------

![Fig 1](images/1.png "Fig 1")

The tool starts with the home screen shown in Fig. 1, waiting for the
user input. To work with the historical mode, one should --

-   Select a date range using the date slider/calendar input box (the
    tool populates the earliest and latest dates available for selection
    by itself, based on the available data).

-   Date ranges less than or equal to 14 days show individual incidents
    (Fig. 3). To avoid cluttering the map, date ranges greater than this
    are shown as heat maps (Fig. 2).

-   Upon selecting the date range, the user should click the submit
    button, which loads the map and the statistics (Fig. 4), as shown in
    the figures below.

![Fig 2](images/2.png "Fig 2")

![Fig 3](images/3.png "Fig 3")

Figure : Incident Map (Date Range \<= 14 days)

Given a date range less than 14 days, the user can also select a subset
of incident types from the side pane (e.g. cardiac, trauma etc.) and
choose to visualize the chosen incident type only, providing more
granularity in visualization.

The summary statistics provide a breakdown of incidents according to
severity in the form of a bar chart, as well as a breakdown of incidents
by category/cause (chest pain, fall, sexual assault, stroke etc.) in the
form of a pie chart.

![Fig 4](images/4.png "Fig 4")

Figure : Summary Statistics of Historical Data

 Prediction Mode
---------------

As highlighted before, the tool has four modes -- historical,
prediction, exploratory and dispatch. In order to change the mode, at
any screen, the user can access the menu bar (using the three horizontal
green bars on the left of the main screen) as shown in Fig. 5. This lets
the user navigate from one mode to the other.

![Fig 5](images/5.png "Fig 5")

Once in the prediction mode, the user can:

-   Select a particular category of incidents (Fig. 6).

-   Move the date slider to a future date, at which the user needs a
    prediction for incident density.

-   Click on the submit button to load the prediction map. The following
    figure shows an example prediction for the "cardiac" incident
    category (Fig. 7).

![Fig 6](images/6.png "Fig 6")

Figure : Choose Prediction Category

![Fig 7](images/7.png "Fig 7")

Figure : Prediction Heat Map

Explore Mode
------------

The explore mode lets the user add a fire station, with the mean number
of responders across existing stations, and calculate its effect on the
response time. In order to do so, the user needs to:

-   Navigate to the explore menu from the menu bar, as shown in Fig 5.

-   If the user wants, she can display the existing fire stations by
    pressing the "show/hide real fire stations" button on the map. This
    loads the existing fire station and responder information. On
    clicking any station, the user can see the responders assigned to
    the station (Fig. 8).

-   Then, user can add a station by clicking the "add a fire station"
    button, and drag the fire station to the desired location (Fig. 9).

-   Finally, on clicking the "Submit a new fire station location"
    button, the user can get the summary of difference in response times
    due to the new station (Fig. 10).

![Fig 8](images/8.png "Fig 8")

Figure : Visualizing existing Fire Stations

![Fig 9](images/9.png "Fig 9")

![Fig 10](images/10.png "Fig 10")

Figure : Response Time Optimization Summary

Dispatch Mode
-------------

The dispatch mode lets the user get real-time guidance on servicing
incidents, that have not been serviced as yet. In order to access this
mode, the user needs to

-   Navigate to the Dispatch mode using the mode menu, as shown in
    Fig. 5.

-   The user can plot the pending incidents using the "Plot Pending
    Incidents" button (Fig. 11).

-   The user can get dispatch guidance by clicking on the "Get Dispatch
    Decisions" button (Fig. 12).

![Fig 11](images/11.png "Fig 11")

![Fig 12](images/12.png "Fig 12")

Figure : Get Dispatch Decisions

Background Jobs - description
=============================

The tool performs three basic background jobs --

Data ingestion.

Prediction Model upgrade.

Overall Monitoring.

We describe the functionalities of these jobs now. We strongly recommend
that these are changed only by the administrators who are in-charge of
the dashboard.

Data Ingestion
--------------

New incident data is transferred from the ImageTrend database to the
server periodically, currently at a rate of every 3 minutes. This
information must be processed and ingested into the dashboard's
database. We developed a service that does this process automatically
called serv\_periodic\_update.service.

There are a few parameters for the service that are set in the
ingest\_config.cfg file (located in
analytics-dashboard/update-services/). We use Darksky for getting the
current weather, and it's api key is configurable. Also, if the rate at
which imagetrend sends updates changes from 3 minutes, the wait\_time
parameter (stored in seconds) can be changed to reflect this in the
ingestion rate. The min\_wait\_time is the minimum number of seconds
between updates, to ensure the server is not overloaded.

Prediction Model Upgrade
------------------------

The prediction model for generating heat maps at future dates is often
times slow to compute on the fly. Hence the tool updates this model at
regular intervals and stores the model, and directly accesses it when
need be. The script analytics-dashboard/streamUpdate.py does this by
calling the required back-end methods of the dashboard. The only
configurable parameter for this process is the update frequency
(measures frequency as the number of times update is done in 24 hours),
and is located in the config file "streamUpdate.conf" located at
analytics-dashboard/update-services. The default value is set to 1,
which means that the model is updated once every 24 hours.

Overall Monitoring
------------------

If the ingestion service stops or fails for some reason, we have set up
a script to send an email notification to a configured email address.
This address, and the sending email address can be updated in the same
ingest\_config.cfg file.

Note - If any of the parameters are updated, the systemd service must be
restarted.

### Requirements
```
pymongo==3.5.0
flask-socketio==2.9.2
requests==2.18.4
pytz==2017.2
numpy==1.13.1
pyproj==1.9.5.1

gtfs-realtime-bindings==0.0.4
protobuf_to_dict==0.1.0
mongoengine==0.10.6
pykalman==0.9.5
numpydoc==0.5
scipy==0.16.1
scikit-learn==0.16.1
```
