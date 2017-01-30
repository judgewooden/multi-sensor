/*
 * Graph
 *
 * This D3 based graphing allows for real-time updates,
 * will filter data based on LPF or tollerance
 * and show data gaps if no data is available
 *
 * by: Douwe de Jong
 *
 */
"use strict";

function LineGraph(argsMap) {
 	/* *************************************************************** */
	/* public methods */
	/* *************************************************************** */
	var self = this;
	var debug= false;

	/* *************************************************************** */
	/* private variables */
	/* *************************************************************** */
	// the div we insert the graph into
	var containerId;
	var container;

	// Detail some behavior
	var myBehavior = {};
	var legendFontSize = 12;
	var transitionDuration = 300;

	// Details of the data
	var data = [];      // D3 data for each line
	var meta = {};      // meta data describing data for each line

	// D3 functions
	var bisectDate = d3.bisector(function(d) { return d.timestamp; }).right;

	// define dimensions
	// var margin = [ 20, 40, 30, 40]; // margins (top, right, bottom, left)
	var marginTop = 20;
	var marginRight = 40;
	var marginBottom = 30;
	var marginLeft = 40;
	var myWidth, myHeight; // Width & height

	// D3 structures
	var graph;
	var xScale, xAxis;
	var yLeft, yAxisLeft, yRight, yAxisRight, hasYAxisLeft, hasYAxisRight;
	var leftYaxis, leftYaxislegend, rightYaxis, rightYaxislegend;

	var color = d3.scale.category20();
	var drawline, theline, linesGroup, lines, linesGroupText;
	var tipLegend, tipGraph;
	var hoverContainer, hoverLine, hoverLineXOffset, hoverLineYOffset,
														hoverLineGroup;
	var titleGraph;
	var lineFunctionSeriesIndex;    // special bodge !!! pay attention to it

	// user behavior
	var menuButtons = [['update','Updating'], ['pause','Pause']];
	var updatePaused = 'update';
	var haltedDuetoError = false;
	var userCurrentlyInteracting = false;
	var currentUserLine = -1;
	var currentUserPositionX = -1;

	// scrolling graph fields
	var myInterval = false;
	var myResizeListener = false;
	var minTime = new Date();
	var maxTime = new Date();

	var lastTimeValue;
	var inProgress = false;

	// Include a spin component when loading data
	var spinner;
	var spinneropts;
	var spinnerActive = true;

	// Filter data values if they are the same value as previous with tollerance ...
	var lastTimestamp;
	var lastValue;
	var smoothedValue;
	var filtercount;

	// Make it possible to modify the axis manually
	// TODO
	var leftYaxisOverideMax=0;   // 0 means disabled
	var leftYaxisControlMaxUp, leftYaxisControlMaxDown, leftYaxisControlMaxReset;
	var leftYaxisOverideMin=0;   // 0 means disabled
	var leftYaxisControlMinUp, leftYaxisControlMinDown, leftYaxisControlMinReset;
	var rightYaxisOverideMax=0;   // 0 means disabled
	var rightYaxisControlMaxUp, rightYaxisControlMaxDown, rightYaxisControlMaxReset;
	var rightYaxisOverideMin=0;   // 0 means disabled
	var rightYaxisControlMinUp, rightYaxisControlMinDown, rightYaxisControlMinReset;
	/* *************************************************************** */
	/* Initiationzation and Validation */
	/* *************************************************************** */
	this.destroy = function() {
		if(myResizeListener != false)
			clearTimeout(myResizeListener);
		if(myInterval != false )
			clearInterval( myInterval );
		var looper = $('#' + containerId)[0];
		while (looper.firstChild) {
			looper.removeChild(looper.firstChild);
		}
	}

	this.setRefreshRate = function(value) {
		if (myInterval != false)
			clearInterval( myInterval );
		myBehavior.interval = value;
		myInterval = setInterval(function () {
				self.refreshData();
		}, myBehavior.interval * 1000);
		self.refreshData();
	}

	var _init = function() {
		containerId = getRequiredVar(argsMap, 'containerId');
		container = document.querySelector('#' + containerId);
		if (container==null) {
			message="Target container not found: " + containerId;
			alert(message);
			throw new Error(message);
		}

		// load the configuration
		loadConfig(getRequiredVar(argsMap, 'data'));

		// Create the Graph
 		createGraph();
		spinner = new Spinner(spinneropts).spin(container);

		// Load data into SQL
		self.refreshData();

		// window resize listener
		
		$(window).resize(function(){
			if(myResizeListener !== false)
				clearTimeout(myResizeListener);
				myResizeListener = setTimeout(handleWindowResizeEvent, 200);
		});

		// Auto update the data if needed
		if ( myBehavior.autoUpdate == 1 ) {
			myInterval = setInterval(function () {
				self.refreshData();
			}, myBehavior.interval * 1000);
		}

	}

	/*
	 * Manager Data Update
	 */
	this.refreshData = function() {
		maxTime = new Date();
		minTime = new Date(maxTime.getTime() - (1000 * myBehavior.secondsToShow));

		if ( inProgress ){
			redrawAxes(false);
			redrawLines(false);
			return;
		}
		inProgress = true;

		// build a single query
		var myurl = [];
		var queryTime;
		for (var key in data) {

			var lastelem = data[key].values.length - 1;

			if (lastelem < 1) {
				queryTime=minTime; //.toMysqlFormat();
			} else {
				queryTime=new Date(data[key].values[lastelem].timestamp); //.toMysqlFormat();
			}
			var temp = {
				codifier: meta.codifier[key],
				key: key,
				time: Date.parse(queryTime)
			};
			myurl.push(temp);
		}
		myurl = JSON.stringify(myurl);
		var u="/sensorts/" + encodeURI( myurl );
		if (debug) console.log(u);

		// Prepare variables for filtering
		var skipped = new Array(data.length);
		var prev = new Array(data.length);
		for (var i = 0; i < data.length; i++) {
			skipped[i] = false;
		}

		$.ajax({
            type : "GET",
            dataType : "json",
            url: u,
            success: function(answer, textStatus, request){
				for (var row = 0; row < answer.length; row++) {
					var key=answer[row][0];

					var temp = {
						timestamp: new Date(+answer[row].t),
						value: +answer[row].v
					};

					//  Low Pass Filter
					if (smoothedValue[key]==null) {
						smoothedValue[key]=temp.value;
					} else {
						smoothedValue[key] = smoothedValue[key] + ( temp.value
											- smoothedValue[key]) / meta.smoothing[key];
						temp.value = smoothedValue[key];
						//trace(key + " Smooth:" + temp.value);
					}

					//  Filter data withing a tollerance range
					if ( meta.filter[key] == -1 ) {
						data[key].values.push(temp);
						lastTimestamp[key]=temp.timestamp;
						lastValue[key]=temp.value;
					} else {
						if ( lastTimestamp[key] == null) {
							data[key].values.push(temp);
							lastTimestamp[key]=temp.timestamp;
							lastValue[key]=temp.value;
							skipped[key]=false;
							//trace(key + " 1st:" + temp.timestamp.getTime() + " V:" + temp.value);
						} else {
							var dif = temp.timestamp.getTime() - lastTimestamp[key].getTime();
							if  (dif > meta.datagap[key]) {
								if ( skipped[key] == true) {
									data[key].values.push(prev[key]);
									lastTimestamp[key]=prev[key].timestamp;
									lastValue[key]=prev[key].value;
									//trace(key + " add:" + prev[key].timestamp.getTime()
									//	+ " V:" + prev[key].value + " diff:" + dif);
									filtercount[key] = filtercount[key] - 1;
								}
							}
							var change=Math.abs(temp.value - lastValue[key]);
							//trace(key + " del:" + change + " L:" + lastValue[key]
							//		+ " V:" + temp.value);
							if (change > meta.filter[key]) {
								data[key].values.push(temp);
								lastTimestamp[key]=temp.timestamp;
								lastValue[key]=temp.value;
								skipped[key]=false;
								//trace(key + " new:" + temp.timestamp.getTime()
								//		+ " V:" + temp.value + " diff:" + dif);
							} else {
								skipped[key]=true;
								filtercount[key] = filtercount[key] + 1;
								prev[key]=temp;
								//trace(key + " hop:" + temp.timestamp.getTime()
								//	+ " V:" + temp.value + " diff:" + dif);
							}
						}
					}
				}
				if ( skipped[key] == true) {
					data[key].values.push(temp);
					lastTimestamp[key]=temp.timestamp;
					lastValue[key]=temp.value;
					filtercount[key] = filtercount[key] - 1;
					skipped[key]=false;
					//trace(key + " end:" + temp.timestamp.getTime()
					//				+ " V:" + temp.value + " diff:" + dif);
				}
				//for (var i = 0; i < data.length; i++)
				//	trace("Total Values Filtered: " +  meta.names[i] + " = " + filtercount[i]);

				redrawAxes(false);
				redrawLines(false);

				$(container).trigger('LineGraph:dataModification');

				// Destroy answer to free up ram
				answer=0;

				//pop old data from our cache
				var elem=0;
				for (var key in data) {
					for (elem in data[key].values) {
						var v1=new Date(data[key].values[elem].timestamp .getTime());
						if (v1>minTime) {
							break;
						}
					}
					if (elem > 0 ) {
						data[key].values.splice(0, elem);
					}
				}

				inProgress = false;
				if (spinnerActive) {
					spinnerActive=false;
					spinner.stop();
				}
			},
			error: function(request, textStatus, errorThrown) {
				trace("Data request failure");
				console.log("Request:", request);
				console.log("Text   :", textStatus);
				console.log("Thrown :", errorThrown);
				alert(" Server response: " + errorThrown);
				if (spinnerActive) {
					spinnerActive=false;
					spinner.stop();
				}
				haltedDuetoError=true;
			}
		});
	}

	/*
	 * Load all the data from SQL using defers before plotting
	 */
	var loadConfig = function(dataMap) {

		// Load data for graph behavior
		myBehavior.title = getOptionalVar(dataMap.Settings, 'Title', "");
		myBehavior.secondsToShow = +getOptionalVar(dataMap.Settings,	'SecondsToShow', "3600");
		myBehavior.autoUpdate = +getOptionalVar(dataMap.Settings, 'AutoUpdate', "0");
		myBehavior.interval = +getOptionalVar(dataMap.Settings, 'UpdateInterval', "5");
		myBehavior.tickLine = +getOptionalVar(dataMap.Settings, 'TickLine', "");
		myBehavior.dateLabel = getOptionalVar(dataMap.Settings, 'DateLabel', "bottom");
		myBehavior.axisLeftMin = +getOptionalVar(dataMap.Settings, 'LeftMin', "");
		myBehavior.axisLeftMax = +getOptionalVar(dataMap.Settings, 'LeftMax', "");
		myBehavior.axisRightMin = +getOptionalVar(dataMap.Settings, 'RightMin', "");
		myBehavior.axisRightMax = +getOptionalVar(dataMap.Settings, 'RightMax', "");
		myBehavior.axisLeftLegend = getOptionalVar(dataMap.Settings, 'LeftLegend', "");
		myBehavior.axisRightLegend = getOptionalVar(dataMap.Settings, 'RightLegend', "");
		myBehavior.interpolation = getOptionalVar(dataMap.Settings, 'Interpolation', "linear");
		myBehavior.hideDateLabel = +getOptionalVar(dataMap.Settings, 'HideDateLabel', "0");
		myBehavior.hideLegend = +getOptionalVar(dataMap.Settings, 'HideLegend', "0");
		myBehavior.hideXAxis = +getOptionalVar(dataMap.Settings, 'HideXAxis', "0");
		myBehavior.hideAxisLeft = +getOptionalVar(dataMap.Settings, 'HideAxisLeft', "0");
		myBehavior.hideAxisRight = +getOptionalVar(dataMap.Settings, 'HideAxisRight', "0");
		myBehavior.hideButtons = +getOptionalVar(dataMap.Settings, 'HideButtons', "1");
		myBehavior.hideLeftControls = +getOptionalVar(dataMap.Settings, 'HideLeftControls', "1");
		myBehavior.hideRightControls = +getOptionalVar(dataMap.Settings, 'HideRightControls', "1");
		if (debug) console.log(containerId, " Behavior: ", myBehavior);

		// Load graph meta data
		meta.names = new Array();
		meta.codifier = new Array();
		meta.yaxes = new Array();
		meta.datagap = new Array();
		meta.filter = new Array();
		meta.smoothing = new Array();
		meta.interpolation = new Array();
		meta.hidden = new Array();
		for (var key in dataMap.Settings.graphSensors) {
			meta.names.push(getRequiredVar(dataMap.Settings.graphSensors[key], 'Name', "Need to plot something"));
			meta.codifier.push(getRequiredVar(dataMap.Settings.graphSensors[key], 'Codifier', "Need to get data from somewhere"));
			meta.yaxes.push(getRequiredVar(dataMap.Settings.graphSensors[key], 'Axis', "Must specify Axis"));
			meta.datagap.push(getRequiredVar(dataMap.Settings.graphSensors[key], 'Frequency', "Must specify [0=valid]"));
			meta.filter.push(getRequiredVar(dataMap.Settings.graphSensors[key], 'Filter', "Must specify [-1=none]"));
			meta.smoothing.push(getRequiredVar(dataMap.Settings.graphSensors[key], 'Smoothing', "Must specify [1=no-effect]"));
			meta.interpolation.push(getRequiredVar(dataMap.Settings.graphSensors[key], 'Interpolation', "Must specify Interpolation"));
			meta.hidden.push(getOptionalVar(dataMap.Settings.graphSensors[key], 'Hidden', "0"));
		}
		if ( meta.length == 0) {
			message="There is no Sensor data found in Settings"
			alert(message);
			throw new Error(message);
		}
		if (debug) console.log(containerId, " Meta: ", meta);

		//Create the data object
		for (var key in meta.names) {
			// Do some data validation checks
			meta.datagap[key]=+meta.datagap[key];
			if ( meta.datagap[key] > 0 ) {
				meta.datagap[key] = meta.datagap[key] * 1000;
			} else {
				meta.datagap[key]=0;
			}

			meta.filter[key]=+meta.filter[key];
			if ( meta.datagap[key] < 0 ) {
				meta.datagap[key] = -1;
			}

			// push each line to the data stack
			var temp = {
				name: meta.names[key],
				codifier: meta.codifier[key],
				yaxis: meta.yaxes[key],
				interpolation: meta.interpolation[key],
				datagap: +meta.datagap[key],
				smoothing: +meta.smoothing[key],
				filter: +meta.filter[key],
				hidden: +meta.hidden[key],
				values: []
			};
			if (debug) console.log(containerId, " Data: ", temp);
			data.push(temp);
	 	}

	 	// Do some data validation checks
	 	if ( myBehavior.autoUpdate > 0 ) {
	 		if ( myBehavior.secondsToShow < 1 ) {
	 			throw new Error("secondsToShow must be provided for autoupdate");
	 		}
	 		if ( myBehavior.interval < 1 ) {
	 			throw new Error("interval must be provided for autoupdate");
	 		}
	 	}

	 	// Prepare margins
		hasYAxisLeft=false;
		hasYAxisRight=false;
		for (var key in meta.yaxes) {
			if ( meta.yaxes[key] == 'Left' ) {
				hasYAxisLeft = true;
			}
			if ( meta.yaxes[key] == 'Right' ) {
				hasYAxisRight = true;
			}
		}
		if ((myBehavior.hideDateLabel==1) & (myBehavior.hideButtons==1) & (myBehavior.title=="")) 
			marginTop=2;
		if (myBehavior.hideLegend==1)
			marginBottom = 17;
		if (myBehavior.hideXAxis==1)
			marginBottom = marginBottom-17;
		if (myBehavior.hideAxisRight==1)
			marginRight=0;
		if (hasYAxisRight==false)
			marginRight=0;
		if (myBehavior.hideAxisLeft==1)
			marginLeft=0;
		if (hasYAxisLeft==false)
			marginLeft=0;
		if (marginTop==2) {
			if ( (hasYAxisLeft==true) & (myBehavior.hideAxisLeft==0) ) {
				if (myBehavior.hideLeftControls==1)
					marginTop=5;
				else
					marginTop=12;
			}
			if ( (hasYAxisRight==true) & (myBehavior.hideAxisRight==0) ) {
				if (myBehavior.hideRightControls==1) {
					if (marginTop<5)
						marginTop=5;
				} else
					marginTop=12;
			}
		}
		if (marginBottom==0) {
			if ( (hasYAxisLeft==true) & (myBehavior.hideAxisLeft==0) ) {
				if (myBehavior.hideLeftControls==1)
					marginBottom=5;
				else
					marginBottom=12;
			}
			if ( (hasYAxisRight==true) & (myBehavior.hideAxisRight==0) ) {
				if (myBehavior.hideRightControls==1) {
					if (marginBottom<5)
						marginBottom=5;
				} else
					marginBottom=12;
			}
		}

	 	// Prepare global variables for filters
		lastTimeValue = new Array(data.length);
		lastTimestamp = new Array(data.length);
		lastValue = new Array(data.length);
		filtercount = new Array(data.length);
	 	smoothedValue = new Array(data.length);
		for (var i = 0; i < data.length; i++) {
			lastTimeValue[i] = null;
			lastTimestamp[i] = null;
			lastValue[i] = null;
			filtercount[i]=0;
			smoothedValue[i] = null;
		}

	}

	/*
	 * Creates the SVG elements
	 */
	var createGraph = function() {

 		initDimensions();

		// Add an SVG element with the desired dimensions and margin.
		graph = d3.select("#" + containerId).append("svg:svg")
			.attr("class", "line-graph")
			.attr("width", myWidth + marginRight + marginLeft)
			.attr("height", myHeight + marginTop + marginBottom)
			.append("svg:g")
			.attr("transform", "translate(" + marginLeft + "," + marginTop + ")");

		if (myBehavior.title != "" ) {
			titleGraph = graph.append("svg:g")
				.attr("class", "title-group")
					.append("text")
					.attr("class", "title")
	        		.attr("x", (myWidth / 2))
	        		.attr("y", 0 - 5)
	        		.attr("text-anchor", "middle")
	        		.text(myBehavior.title);

	    }

	    // X - Axis
		if ( myBehavior.secondsToShow != 0 ) {
			maxTime = new Date();
			minTime.setSeconds(maxTime.getSeconds() - myBehavior.secondsToShow);
		}

		initX();

		graph.append("svg:g")
			.attr("class", "x axis")
			.attr("transform", "translate(0," + myHeight + ")")
			.call(xAxis);

		initY();

		// Add the y-axis to the left
		if (hasYAxisLeft) {
			leftYaxis = graph.append("svg:g")
				.attr("class", "y axis left")
				.attr("transform", "translate(-5,0)")
				.call(yAxisLeft);

			if (myBehavior.hideAxisLeft == 1)
				leftYaxis.attr("class", "y-none axis left");
			else {
				leftYaxislegend = leftYaxis.append("text")
					.attr("class", "y-left-legend")
			    	.attr("transform", "rotate(-90)")
			    	.attr("y", 4)
			    	.attr("x", -8)
			    	.attr("dy", ".71em")
			   		.style("text-anchor", "end")
			    	.text(myBehavior.axisLeftLegend);

				if (myBehavior.hideLeftControls != 1) {
					leftYaxisControlMinUp = leftYaxis.append("svg:text")
						.attr("class", "y-left-control-max-up")
				   		.style("text-anchor", "middle")
				    	.attr("y", myHeight+12)
				    	.attr("x", -25)
				    	.on('click', function(d) {
							leftYaxisOverideMin=yLeft.domain()[0] + ((yLeft.domain()[1] - yLeft.domain()[0])/5);
							redrawAxes(true);
							redrawLines(true);
				    	})
				    	.text(String.fromCharCode(10750));
					leftYaxisControlMinDown = leftYaxis.append("text")
						.attr("class", "y-left-control-max-down")
				   		.style("text-anchor", "middle")
				    	.attr("y", myHeight+12)
				    	.attr("x", -5)
				    	.on('click', function(d) {
							leftYaxisOverideMin=yLeft.domain()[0] - ((yLeft.domain()[1] - yLeft.domain()[0])/5);
							redrawAxes(true);
							redrawLines(true);
				    	})
				    	.text(String.fromCharCode(10751));
					leftYaxisControlMinReset = leftYaxis.append("text")
				   		.style("text-anchor", "middle")
						.attr("class", "y-left-control-max-reset")
				    	.attr("y", myHeight+12)
				    	.attr("x", -15)
				    	.on('click', function(d) {
							leftYaxisOverideMin=0
							redrawAxes(true);
							redrawLines(true);
				    	})
				    	.text(String.fromCharCode(11038));
					leftYaxisControlMaxUp = leftYaxis.append("svg:text")
						.attr("class", "y-left-control-max-up")
				   		.style("text-anchor", "middle")
				    	.attr("y", -6)
				    	.attr("x", -25)
				    	.on('click', function(d) {
							leftYaxisOverideMax=yLeft.domain()[1] + ((yLeft.domain()[1] - yLeft.domain()[0])/5);
							redrawAxes(true);
							redrawLines(true);
				    	})
				    	.text(String.fromCharCode(10750));
					leftYaxisControlMaxDown = leftYaxis.append("text")
						.attr("class", "y-left-control-max-down")
				   		.style("text-anchor", "middle")
				    	.attr("y", -6)
				    	.attr("x", -5)
				    	.on('click', function(d) {
							leftYaxisOverideMax=yLeft.domain()[1] - ((yLeft.domain()[1] - yLeft.domain()[0])/5);
							redrawAxes(true);
							redrawLines(true);
				    	})
				    	.text(String.fromCharCode(10751));
					leftYaxisControlMaxReset = leftYaxis.append("text")
				   		.style("text-anchor", "middle")
						.attr("class", "y-left-control-max-reset")
				    	.attr("y", -6)
				    	.attr("x", -15)
				    	.on('click', function(d) {
							leftYaxisOverideMax=0
							redrawAxes(true);
							redrawLines(true);
				    	})
				    	.text(String.fromCharCode(11038));
				}
			}
		}

		// Add the y-axis to the right
		if (hasYAxisRight) {
			rightYaxis = graph.append("svg:g")
				.attr("class", "y axis right")
				.attr("transform", "translate(" + (myWidth+10) + ",0)")
				.call(yAxisRight)

			if (myBehavior.hideAxisRight == 1)
				rightYaxis.attr("class", "y-none axis right");
			else {
				rightYaxislegend = rightYaxis.append("text")
					.attr("class", "y-right-legend")
			    	.attr("transform", "rotate(-90)")
			    	.attr("y", -12)
			    	.attr("x", -8)
			    	.attr("dy", ".71em")
			   		.style("text-anchor", "end")
			    	.text(myBehavior.axisRightLegend);

				if (myBehavior.hideRightControls != 1) {
					rightYaxisControlMinUp = rightYaxis.append("svg:text")
						.attr("class", "y-right-control-max-up")
				   		.style("text-anchor", "middle")
				    	.attr("y", myHeight+12)
				    	.attr("x", 5)
				    	.on('click', function(d) {
							rightYaxisOverideMin=yRight.domain()[0] + ((yRight.domain()[1] - yRight.domain()[0])/5);
							redrawAxes(true);
							redrawLines(true);
				    	})
				    	.text(String.fromCharCode(10750));
					rightYaxisControlMinDown = rightYaxis.append("text")
						.attr("class", "y-right-control-max-down")
				   		.style("text-anchor", "middle")
				    	.attr("y", myHeight+12)
				    	.attr("x", 25)
				    	.on('click', function(d) {
							rightYaxisOverideMin=yRight.domain()[0] - ((yRight.domain()[1] - yRight.domain()[0])/5);
							redrawAxes(true);
							redrawLines(true);
				    	})
				    	.text(String.fromCharCode(10751));
					rightYaxisControlMinReset = rightYaxis.append("text")
				   		.style("text-anchor", "middle")
						.attr("class", "y-right-control-max-reset")
				    	.attr("y", myHeight+12)
				    	.attr("x", 15)
				    	.on('click', function(d) {
							rightYaxisOverideMin=0
							redrawAxes(true);
							redrawLines(true);
				    	})
				    	.text(String.fromCharCode(11038));
					rightYaxisControlMaxUp = rightYaxis.append("svg:text")
						.attr("class", "y-right-control-max-up")
				   		.style("text-anchor", "middle")
				    	.attr("y", -6)
				    	.attr("x", 5)
				    	.on('click', function(d) {
							rightYaxisOverideMax=yRight.domain()[1] + ((yRight.domain()[1] - yRight.domain()[0])/5);
							redrawAxes(true);
							redrawLines(true);
				    	})
				    	.text(String.fromCharCode(10750));
					rightYaxisControlMaxDown = rightYaxis.append("text")
						.attr("class", "y-right-control-max-down")
				   		.style("text-anchor", "middle")
				    	.attr("y", -6)
				    	.attr("x", 25)
				    	.on('click', function(d) {
							rightYaxisOverideMax=yRight.domain()[1] - ((yRight.domain()[1] - yRight.domain()[0])/5);
							redrawAxes(true);
							redrawLines(true);
				    	})
				    	.text(String.fromCharCode(10751));
					rightYaxisControlMaxReset = rightYaxis.append("text")
				   		.style("text-anchor", "middle")
						.attr("class", "y-right-control-max-reset")
				    	.attr("y", -6)
				    	.attr("x", 15)
				    	.on('click', function(d) {
							rightYaxisOverideMax=0
							redrawAxes(true);
							redrawLines(true);
				    	})
				    	.text(String.fromCharCode(11038));
				}
			}
		}

		// Create automated color domain
		color.domain(meta.names);

		// Remember to use the bodge !!!
		lineFunctionSeriesIndex  = -1;
		// Create the line function() !!! Remember lineFunctionSeriesIndex bodge
		// NOTE: This is a serious bodge !!! but it works

      	theline = d3.svg.line()
            .defined(function(d, i) {
            	// If there is no data for a certain while (stop interpolation !!)
//				trace("defined: " + containerId + " => i: " + lineFunctionSeriesIndex);
            	if (meta.datagap[lineFunctionSeriesIndex] > 0 ) {
            		if (lastTimeValue[lineFunctionSeriesIndex] != null) {
            			var dif = d.timestamp.getTime() - lastTimeValue[lineFunctionSeriesIndex].getTime();
	        			if (dif > meta.datagap[lineFunctionSeriesIndex]) {
/*            				trace("defined: " + containerId +
            					" => i: " + lineFunctionSeriesIndex +
            					" diff: " + dif +
            					" last: " + lastTimeValue[lineFunctionSeriesIndex].getTime() +
            					" curr: " + d.timestamp.getTime());
*/
            				lastTimeValue[lineFunctionSeriesIndex] = null;
            				return false;
            			}
            		}
            		lastTimeValue[lineFunctionSeriesIndex] = d.timestamp;
             		return true;
             	} else {
             		return true;
             	}
            })
			.x( function(d, i) { return xScale(d.timestamp); })
			.y( function(d, i) {
				// DOUWE (x?)
				//trace( "y-axis: " + lineFunctionSeriesIndex );
				if ( i == 0 ) {
					lineFunctionSeriesIndex++;
				}
				if ( meta.yaxes[lineFunctionSeriesIndex]  == "Right" ) {
					return yRight(d.value);
				} else {
					return yLeft(d.value);
				}
			});

		// Remember to use the bodge !!!
		lineFunctionSeriesIndex  = -1;

	    // Customer Interpolation routines per line ...
	    if ( myBehavior.interpolation == "custom" ) {
			drawline = theline
	        .interpolate(function(points) {
	            if ( meta.interpolation[lineFunctionSeriesIndex] == "step") {
	            	//trace(lineFunctionSeriesIndex + " - step");
					var i = 0,
					    n = points.length,
					    p = points[0],
					    path = [p[0], ",", p[1]];
					while (++i < n) path.push("H", (p[0] + (p = points[i])[0]) / 2, "V", p[1]);
					if (n > 1) path.push("H", p[0]);
					return path.join("");
				} else {
	            	//trace(lineFunctionSeriesIndex + " - linear");
	            	return points.join("L");
	            }
	        })
	    } else {
           	// trace(container + ": " + lineFunctionSeriesIndex + " - " + myBehavior.interpolation);
			drawline = theline
				.interpolate(myBehavior.interpolation);
		}

		// Draw the line
		lines = graph.append("svg:g")
			.attr("class", "lines")
			.selectAll("path")
			.data(data);

		// Create a hover line
		hoverContainer = container.querySelector('g .lines');

		$(container).mouseleave(function(event) {
			handleMouseOutGraph(event);
		});

		$(container).mousemove(function(event) {
			handleMouseOverGraph(event);
		});

		linesGroup = lines.enter().append("g")
			.attr("class", function(d, i) {
				return "line_group series_" + i;
			});

		linesGroup.append("path")
			.attr("class", function(d, i) {
				return "line series_" + i;
			})
			.attr("id", function(d,i) {
				return (containerId + meta.names[i]);
			})
			.style("opacity", function(d, i) {
				var newOpacity = meta.hidden[i]=="1" ? 0 : 1;
				return newOpacity;
			})
			.attr("fill", "none")
			.attr("stroke", function(d, i) {
				return color(meta.names[i]);
			})
			.attr("d", function(d, i) {
				return drawline(d.values)
			})
			.on('mouseover', function(d,i) {
				handleMouseOverLine(d,i);
			});

		// add line label to line group
		linesGroupText = linesGroup.append("svg:text");
		linesGroupText.attr("class", function(d, i) {
			return "line_label series_" + i;
		})
		.text(function(d, i) {
			return "";
		});

		hoverLineGroup = graph.append("svg:g")
			.attr("class", "hover-line");

		hoverLine = hoverLineGroup
			.append("svg:line")
			.attr("x1", 10).attr("x2", 10)
			.attr("y1", 0).attr("y2", myHeight);

		hoverLine.classed("hide", true);

		// Call functions to do additional data
		if (myBehavior.hideDateLabel==0) 
			createDateLabel();

		if (myBehavior.hideLegend==0)
			createLegend();
		// only show menu if we are updating
		if ( myBehavior.autoUpdate == 1 ) {
			if (myBehavior.hideButtons != 1) {
				createMenuButtons();
			}
		}

		setValueLabelsToLatest();

	}

	/**
	* Called when the window is resized to redraw graph accordingly.
	*/
	var handleWindowResizeEvent = function() {
		//trace("Window Resize Event [" + containerId + "] => resizing graph")
		initDimensions();
		initX();
		initY();

		// reset width/height of SVG
		d3.select("#" + containerId + " svg")
			.attr("width", myWidth + marginRight + marginLeft)
			.attr("height", myHeight + marginTop + marginBottom);

		// OOO reset transform of x axis
		graph.selectAll("g .x.axis")
			.attr("transform", "translate(0," + myHeight + ")");

		if (hasYAxisRight) {
			graph.selectAll("g .y.axis.right")
				.attr("transform", "translate(" + (myWidth+10) + ",0)");
		}

		legendFontSize = 12;
		graph.selectAll("text.legend.name")
			.attr("font-size", legendFontSize);
		graph.selectAll("text.legend.value")
			.attr("font-size", legendFontSize);

		if (myBehavior.dateLabel=="bottom") {
			var yDate=myHeight+marginBottom-2;
			var xDate=120;
		} else {
			var yDate=-4;
			var xDate=myWidth-5;
		}
		graph.select('text.date-label')
			.transition()
			.duration(transitionDuration)
			.ease("linear")
			.attr("x", xDate)
			.attr("y", yDate);

		if (myBehavior.title != "" ) {
			graph.select('text.title')
				.transition()
				.duration(transitionDuration)
				.ease("linear")
	        	.attr("x", (myWidth / 2));
	    }

		redrawAxes(true);
		redrawLines(true);
		redrawLegendPosition(true);
		setValueLabelsToLatest(true);
	}

	var redrawLines = function(withTransition) {
		lineFunctionSeriesIndex  = -1; // Remember this bodge !!!

		// redraw lines
		if(withTransition) {
			graph.selectAll("g .lines path")
				.transition()
					.duration(transitionDuration)
					.ease("cubic")
					.attr("d", function(d, i) {
						return drawline(d.values)
					})
					.attr("transform", null);
		} else {
			graph.selectAll("g .lines path")
				.attr("d", function(d, i) {
					return drawline(d.values)
				})
				.attr("transform", null);
		}
	}

	/**
     * Create menu buttons
	 */
	var createMenuButtons = function() {
		var cumulativeWidth = 0;

		var buttonMenu = graph.append("svg:g")
				.attr("class", "menu-group")
			.selectAll("g")
				.data(menuButtons)
			.enter().append("g")
				.attr("class", "menu-buttons")
			.append("svg:text")
				.attr("class", "menu-button")
				.text(function(d, i) {
					return d[1];
				})
				.attr("font-size", "12")
				.attr("fill", function(d) {
					if (d[0] == updatePaused ) {
						return "black";
					} else {
						return "blue";
					}
				})
				.classed("selected", function(d) {
					if (d[0] == updatePaused ) {
						return true;
					} else {
						return false;
					}
				})
				.attr("x", function(d, i) {
					var returnX = cumulativeWidth;
					cumulativeWidth += this.getComputedTextLength()+5;
					return returnX;
				})
				.attr("y", -4)
				.on('click', function(d, i) {
					handleMouseClickMenuButton(this, d, i);
				});
	}

	var handleMouseClickMenuButton = function(button, buttonData, index) {
		var cumulativeWidth = 0;

		if(index == 0) {
			// start update
			updatePaused='update';
			myInterval = setInterval(function () {
				self.refreshData();
			}, myBehavior.interval * 1000);
		} else if(index == 1){
			updatePaused='pause';
			// pause update
			clearInterval( myInterval );
			myInterval=false;
		}

		graph.selectAll('.menu-button')
			.text(function(d, i) {
				if (i == 0) {
					if (updatePaused == "update" ) {
						return "Updating";
					} else {
						return "Update";
					}
				} else {
					if (updatePaused == "update" ) {
						return "Pause";
					} else {
						return "Paused";
					}
				}
			})
			.attr("font-size", "12")
			.attr("fill", function(d) {
				if (d[0] == updatePaused ) {
					return "black";
				} else {
					return "blue";
				}
			})
			.classed("selected", function(d) {
				if (d[0] == updatePaused ) {
					return true;
				} else {
					return false;
				}
			})
			.attr("x", function(d, i) {
				var returnX = cumulativeWidth;
				cumulativeWidth += this.getComputedTextLength()+5;
				return returnX;
			})
	}

	/**
	 * Create a legend that displays the name of each line with appropriate colo
	 * and allows for showing the current value when doing a mouseOver
	 */
	var createLegend = function() {

		tipLegend = d3.tip()
  			.attr('class', 'd3-tip')
  			.offset([-10, 0])
  			.html(function(d) {
				for (var key in meta.names) {
					if (d == meta.names[key]) {
						var hint;
		// indent for convenience
		hint="<strong style='color:red;font-size:10px'>Sensor: "+d+"</strong><br>";
		hint+="<span style='font-size:10px'>";
		hint+="Status: ";
		if ( meta.hidden[key]=="1")
			hint+="Hidden<br><br>";
		else
			hint+="Shown<br><br>";
    	hint+="Codifier: "+ data[key].codifier + "<br><br>";
    	hint+="Interpolation: ";
    	if ( myBehavior.interpolation == "custom" )
    		hint+=data[key].interpolation + "<br>";
    	else
    		hint+=myBehavior.interpolation + "<br>";
    	hint+="LPF smoothing: " + data[key].smoothing + "<br><br>";
    	hint+="Filter tolerance: ";
    	if ( data[key].filter == -1 )
    		hint+="Off<br>";
    	else
    		hint+=data[key].filter + "<br>";
    	hint+="Update frequency: " + data[key].datagap/1000 + " seconds<br>";
    	hint+="Values removed: " + filtercount[key] + "<br><br>";
    	var i=data[key].values.length - 1;
    	hint+="Last Update: ";
    	if (i>0) hint+=data[key].values[i].timestamp.toLocaleTimeString();
    	hint+="<br>Last Value: "
    	if (i>0) hint+=afronden(data[key].values[i].value);
    	hint+="<br><br>Total Value Shown: " + afronden(data[key].values.length);
    	hint+="</span>";
    	// end indent
    					return hint;
					}
				}
				return "Value not found";
  		})

		graph.call(tipLegend);

		var legendLabelGroup = graph.append("svg:g")
			.attr("class", "legend-group")
			.selectAll("g")
			.data(meta.names)
			.enter().append("g")
			.attr("class", "legend-labels")

		legendLabelGroup.append("svg:text")
			.attr("class", "legend name")
			.text(function(d, i) {
				return d;
			})
			.attr("font-size", legendFontSize)
			.attr("fill", function(d, i) {
				return color(meta.names[i]);
			})
			.attr("y", function(d, i) {
				return myHeight+marginBottom-2; // 28;
			})
			.style("opacity", function() {
				if ( myBehavior.hideLegend == 1 ) return "0";
				return "1";
			})
			.on('mouseover', tipLegend.show)
      		.on('mouseout', tipLegend.hide)
      		.on("click", function(d) {
      			for (var key in meta.names) {
					if (d == meta.names[key]) {
						var newOpacity;
						if (meta.hidden[key]=="1") {
							data[key].hidden=0;
							meta.hidden[key]=0;
							newOpacity=1;
						}
						else {
							data[key].hidden=1;
							meta.hidden[key]=1;
							newOpacity=0;
						}
						var toselect="#" + containerId + d;
						d3.select(toselect).style("opacity", newOpacity);
					}
				}
      		})

		legendLabelGroup.append("svg:text")
			.attr("class", "legend value")
			.attr("font-size", legendFontSize)
			.style("opacity", function() {
				if ( myBehavior.hideLegend == 1 ) return "0";
				return "1";
			})
			.attr("fill", function(d, i) {
				return color(meta.names[i]);
				})
			.attr("y", function(d, i) {
				return myHeight+marginBottom-2; // 28;
			})
	}

	var redrawLegendPosition = function(animate) {
		var legendText = graph.selectAll('g.legend-group text');
			if(animate) {
				legendText.transition()
					.duration(transitionDuration)
					.ease("linear")
					.attr("y", function(d, i) {
						return myHeight+marginBottom-2; // 28;
					});
			} else {
				legendText.attr("y", function(d, i) {
					return myHeight+marginBottom-2; // 28;
				});
			}
	}

	/**
	 * Create a data label
	 */
	var createDateLabel = function() {

		tipGraph = d3.tip()
  			.attr('class', 'd3-tip')
  			.offset([-10, 0])
  			.direction('s')
  			.html(function(d) {
				var hint;
				// indent for convenience
				hint="<strong style='color:red;font-size:10px'>" + myBehavior.title + "</strong><br><br>";
				hint+="<span style='font-size:10px'>";
				hint+="Show: " + myBehavior.secondsToShow + " seconds<br><br>";
				hint+="Auto update: ";
				if (myBehavior.autoUpdate == 1)
					hint+="On<br>";
				else
					hint+="Off<br>";
				hint+="Update Interval: " + myBehavior.interval + " seconds<br>"
				hint+="Currently : "
				if (updatePaused == "pause")
					hint+="Paused<br><br>";
				else
					if (haltedDuetoError)
						hint+="Halted Due to Error<br><br>";
					else
						hint+="Updating<br><br>";
				return hint;
			})

		graph.call(tipGraph);

		var date = new Date();

		if (myBehavior.dateLabel=="bottom") {
			var yDate=myHeight+marginBottom-2;
			var xDate=120;
		} else {
			var yDate=-4;
			var xDate=myWidth-5;
		}
		var buttonGroup = graph.append("svg:g")
			.attr("class", "date-label-group")
			.append("svg:text")
			.attr("class", "date-label")
			.attr("text-anchor", "end")
			.attr("font-size", "10")
			.attr("y", yDate)
			.attr("x", xDate)
			// .style("opacity", function() {
			// 	if ( myBehavior.hideDateLabel == 1 ) return "0";
			// 	return "1";
			// })
			.text(date.toDateString() + " " + date.toLocaleTimeString())
			.on('mouseover', tipGraph.show)
      		.on('mouseout', tipGraph.hide)
	}

	/**
	 * Called when a user mouses over a Legend.
	 * TODO: Think this is no longer used
	 */
	var handleMouseOverLegend = function(legendData, index) {
		trace("MouseOver Legend [" + containerId + "] => " + index + " Legend:" + legendData);
	}

	/**
	 * Called when a user mouses over a line.
	 */
	var handleMouseOverLine = function(lineData, index) {
//		trace("MouseOver line [" + containerId + "] => " + index);
		userCurrentlyInteracting = true;
		currentUserLine=index;
	}

	/**
	* Called when a user mouses over the graph.
	*/
	var handleMouseOverGraph = function(event) {
		var mouseX = event.pageX-hoverLineXOffset;
		var mouseY = event.pageY-hoverLineYOffset;

/*
		trace("MouseOver graph [" + containerId + "] => x: " + mouseX +
			" y: " + mouseY + "  height: " + h + " event.clientY: " +
			event.clientY + " offsetY: " + event.offsetY + " pageY: " +
			event.pageY + " hoverLineYOffset: " + hoverLineYOffset);
*/
		if(mouseX >= 0 && mouseX <= myWidth && mouseY >= 0 && mouseY <= myHeight) {
			hoverLine.classed("hide", false);

			// set position of hoverLine
			hoverLine.attr("x1", mouseX).attr("x2", mouseX);
			displayValueLabelsForPositionX(mouseX);

			// user is interacting
			currentUserPositionX = mouseX;
		} else {
			handleMouseOutGraph(event)
		}
	}

	/**
	* Called when a user mouses moves out the graph.
	*/
	var handleMouseOutGraph = function(event) {

		hoverLine.classed("hide", true);
		setValueLabelsToLatest();

		userCurrentlyInteracting = false;
		currentUserPositionX = -1;
	}

	/**
	 * Set the value labels to whatever the latest data point is.
	 */
	var setValueLabelsToLatest = function(withTransition) {
		displayValueLabelsForPositionX(myWidth, withTransition);
	}

	/**
	 * Convert back from an X position on the graph to a data value from
	 *	the given array (one of the lines)
	 * Return {value: value, date, date}
	 */
	var getValueForPositionXFromData = function(xPosition, index) {
		var xValue = xScale.invert(xPosition);
//		trace("Start get Value. Position: " + xPosition + " Index: " + index);
		var i = bisectDate(data[index].values, xValue, 1);
		var v;
		if (i>1) {
			v=afronden(data[index].values[i-1].value);
		} else {
			v = 0;
		}
		return {value: v, date: xValue };
	}

	/**
	 * Display the data values at position X in the legend value labels.
	 */
	var displayValueLabelsForPositionX = function(xPosition, withTransition) {
		if (myBehavior.hideLegend == 1) return;
		var animate = false;
		if(withTransition != undefined) {
			if(withTransition) {
				animate = true;
			}
		}

//		trace("Label: [" + containerId + "], " + xPosition);

		var dateToShow;
		var labelValueWidths = [];

		graph.selectAll("text.legend.value")
			.text(function(d, i) {
				var valuesForX = getValueForPositionXFromData(xPosition, i);
					dateToShow = valuesForX.date;
					return valuesForX.value;
			})
			.attr("x", function(d, i) {
				labelValueWidths[i] = this.getComputedTextLength();
			})
			.attr("font-weight", function(d, i) {
				if (currentUserLine==i && userCurrentlyInteracting) return "bold";
				return "normal"
			})

		// position label names
		var cumulativeWidth = 0;
		var labelNameEnd = [];

		graph.selectAll("text.legend.name")
			.attr("x", function(d, i) {
				var returnX = cumulativeWidth;
					cumulativeWidth += this.getComputedTextLength()
						+4+labelValueWidths[i]+8;
					labelNameEnd[i] = returnX + this.getComputedTextLength()+5;
				return returnX;
			})
			.attr("font-weight", function(d, i) {
				if (currentUserLine==i && userCurrentlyInteracting) return "bold";
				return "normal"
			})

		cumulativeWidth = cumulativeWidth - 8;
		if(cumulativeWidth > myWidth) {
			legendFontSize = legendFontSize-1;

			graph.selectAll("text.legend.name")
				.attr("font-size", legendFontSize);

			graph.selectAll("text.legend.value")
				.attr("font-size", legendFontSize);

			displayValueLabelsForPositionX(xPosition);
			return;
		}

		graph.selectAll("text.legend.value")
			.attr("x", function(d, i) {
				return labelNameEnd[i];
			})

		graph.select('text.date-label')
			.text(dateToShow.toDateString() + " "
				+ dateToShow.toLocaleTimeString())

		if(animate) {
			graph.selectAll("g.legend-group g")
				.transition()
				.duration(transitionDuration)
				.ease("linear")
				.attr("transform", "translate(" + (myWidth-5-cumulativeWidth) +",0)")
		} else {
			graph.selectAll("g.legend-group g")
				.attr("transform", "translate(" + (myWidth-5-cumulativeWidth) +",0)")
		}
	}

	/*
	 * Allow re-initialzing the y function at any time
	 */
	var initY = function() {

		if (hasYAxisLeft) {
			yLeft = d3.scale
				.linear()
				.domain([
					d3.min(data.filter( function (f) {
						return f.yaxis == 'Left';
					}), function(m) {
						if ( leftYaxisOverideMin == 0 ) {
							var lValue=d3.min(m.values, function(v) {
									return v.value;
							});
							if ( lValue < myBehavior.axisLeftMin || myBehavior.axisLeftMin == 0)
								return lValue;
							else
								return myBehavior.axisLeftMin;
						} else
						    return leftYaxisOverideMin;
					}),
					d3.max(data.filter( function (f) {
						return f.yaxis == 'Left';
					}), function(m) {
						if ( leftYaxisOverideMax == 0 ) {
							var lValue=d3.max(m.values, function(v) {
								return v.value;
							});
							if ( lValue > myBehavior.axisLeftMax || myBehavior.axisLeftMax == 0 )
								return lValue;
							else
								return myBehavior.axisLeftMax;
						} else
						    return leftYaxisOverideMax;
					})
				])
				.range([myHeight, 0])
				.nice();

			yAxisLeft = d3.svg.axis().scale(yLeft).orient("left");

			if (myBehavior.hideAxisLeft == 1) {
				yAxisLeft.tickFormat("");
				yAxisLeft.tickSize(0);
			}
		}

		if (hasYAxisRight) {
			yRight = d3.scale
				.linear()
				.domain([
					d3.min(data.filter( function (f) {
						return f.yaxis == 'Right';
					}), function(m) {
						if ( rightYaxisOverideMin == 0 ) {
							var lValue=d3.min(m.values, function(v) {
									return v.value;
							});
							if ( lValue < myBehavior.axisRightMin || myBehavior.axisRightMin == 0)
								return lValue;
							else
								return myBehavior.axisRightMin;
						} else
							return rightYaxisOverideMin;
					}),
					d3.max(data.filter( function (f) {
						return f.yaxis == 'Right';
					}), function(m) {
						if ( rightYaxisOverideMax == 0 ) {
							var lValue=d3.max(m.values, function(v) {
								return v.value;
							});
							if ( lValue > myBehavior.axisRightMax || myBehavior.axisRightMax == 0)
								return lValue;
							else
								return myBehavior.axisRightMax;
						} else
							return rightYaxisOverideMax;
					})
				])
				.range([myHeight, 0])
				.nice();

			yAxisRight = d3.svg.axis().scale(yRight).orient("right");

			if (myBehavior.hideAxisRight == 1) {
				yAxisRight.tickFormat("");
				yAxisRight.tickSize(0);
			}
		}
	}

	/*
	 * Allow re-initialzing the x function at any time
	 */
	var initX = function() {

		if ( myBehavior.secondsToShow != 0 ) {
//			trace("Start:" + minTime + " End:" + maxTime);
			xScale = d3.time.scale()
				.domain([minTime,maxTime])
				.range([0, myWidth]);
		} else {
			xScale = d3.time.scale()
				.domain([
					d3.min(data, function(m) {
						return d3.min(m.values, function(v) {
							return v.timestamp;
						});
					}),
					d3.max(data, function(m) {
						return d3.max(m.values, function(v) {
							return v.timestamp;
						});
					})
				])
				.range([0, myWidth]);
		}

		if ( myBehavior.tickLine != 0 ) {
			xAxis = d3.svg.axis()
				.scale(xScale)
				.tickSize(-myHeight)
				.tickSubdivide(myBehavior.tickLine);
		} else {
			xAxis = d3.svg.axis()
				.scale(xScale);
		}
		//TODO GET THIS RIGHT
		if ( myBehavior.hideXAxis == 1) {
			xAxis.tickFormat("");
			xAxis.tickSize(0);
		}

	}

	var redrawAxes = function(withTransition) {
		initY();
		initX();

		if(withTransition) {
		// slide x-axis to updated location
			graph.selectAll("g .x.axis").transition()
				.duration(transitionDuration)
				.ease("linear")
				.call(xAxis)

			if (hasYAxisLeft) {
				graph.selectAll("g .y.axis.left").transition()
					.duration(transitionDuration)
					.ease("linear")
					.call(yAxisLeft)
			}
			if (hasYAxisRight) {
				graph.selectAll("g .y.axis.right").transition()
					.duration(transitionDuration)
					.ease("linear")
					.call(yAxisRight)
			}
		} else {
			graph.selectAll("g .x.axis")
				.call(xAxis)

			if (hasYAxisLeft) {
				graph.selectAll("g .y.axis.left")
					.call(yAxisLeft)
			}

			if (hasYAxisRight) {
				graph.selectAll("g .y.axis.right")
					.call(yAxisRight)
			}
		}
	}

	/*
	 * Set height/width dimensions based on container
	 */
	var initDimensions = function() {
		// automatically size to the container using JQuery to get width/height
		myWidth = $("#" + containerId).width() - marginLeft - marginRight; // width
		myHeight = $("#" + containerId).height() - marginTop - marginBottom; // height

		// make sure to use offset() and not position() as we want it relative
		//	to the document, not its parent
		hoverLineXOffset = marginBottom+$(container).offset().left;
		hoverLineYOffset = marginTop+$(container).offset().top;
	}

	/*
	 * Return the value from argsMap for key or throw error if no value found
	 */
 	var getRequiredVar = function(argsMap, key, message) {
		if(!argsMap[key]) {
			if(!message) {
				throw new Error(key + " is required");
			} else {
				throw new Error(message);
			}
		} else {
			return argsMap[key];
		}
	}

	/*
	 * Return the value from argsMap for key or defaultValue if no value found
	 */
	var getOptionalVar = function(argsMap, key, defaultValue) {
		if(!argsMap[key]) {
			key='graph' + key;
			if(!argsMap[key]) {
				return defaultValue;
			} else {
				return argsMap[key];
			}
		} else {
			return argsMap[key];
		}
	}

	var afronden = function( inputValue ) {
		if (inputValue > 10)
			return  Math.round(inputValue * 10) / 10;
		else {
			if (inputValue > 1)
				return Math.round(inputValue * 100) / 100;
			else
				return Math.round(inputValue * 1000) / 1000;
		}
	}

	/*
	 * programmers stuff
	 */
	var error = function(message) {
		console.log("ERROR: ", message)
	}

	var trace = function(message) {
		console.log("DEBUG: ",  message)
	}

	/*
	 * function to create SQL date format
	 */
	function twoDigits(d) {
		if(0 <= d && d < 10) return "0" + d.toString();
		if(-10 < d && d < 0) return "-0" + (-1*d).toString();
		return d.toString();
	}

/* *************************************************************** */
/* execute init now that everything is defined */
/* *************************************************************** */
	_init();


}

