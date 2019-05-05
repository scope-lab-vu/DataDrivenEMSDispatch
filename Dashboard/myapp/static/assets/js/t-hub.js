var socket;
var vehicle_location_timer;
$(document).ready(function() {
    socket = io.connect('http://' + document.domain + ':' + location.port);
    clearTimeout(vehicle_location_timer);

    // socket.emit('get_all_route_segments');

    socket.on('draw_all_route_segments', function(msg) {
    	console.log("socket.on('draw_all_route_segments')");
    	draw_all_route_segments(msg.data);
    	socket.emit('get_all_routeid');
    });
    socket.on('response_map_routes', function(msg) {
    	console.log("socket.on('response_map_routes')");
    	draw_heatmap(msg.data, msg.performance);
    });
    socket.on('all_routeid', function(msg) {
		update_route_dropdown(msg.data);
    });
    socket.on('directions_for_routeid', function(msg) {
		update_direction_dropdown(msg.data);
    });
    socket.on('trips_for_routeid_direction', function(msg) {
    	console.log(msg);
		update_trip_dropdown(msg.tripids, msg.departuretimes);
    });
    socket.on('predictions_for_trip', function(msg) {
    	console.log("socket.on('predictions_for_trip')");
    	console.log(msg);
    	clear_map();
    	draw_all_route_segments(msg.segments);
    	draw_stops(msg.coordinates);
    	console.log("msg.segments");
    	console.log(msg.segments);
    	$("#prediction-div").html("");
    	$("#prediction-div").append(msg.prediction);
    });
    socket.on('simulated_time', function(msg) {
    	console.log(msg);
		update_simulated_time(msg.timestamp);
    });
    socket.on('vehicle_location_for_trip', function(msg) {
    	// console.log(msg);
		// update_simulated_time(msg.timestamp);
	update_vehicle_location(msg.coordinate);
    });
});

function update_simulated_time(ts) {
	$("#time-label").html(ts);
}



var map;

function initMap() {

  // Create an array of styles.
  var styles = [
    {
      stylers: [
        { hue: "#00ffe6" },
        { saturation: -20 }
      ]
    },{
      featureType: "road",
      elementType: "geometry",
      stylers: [
        { lightness: 100 },
        { visibility: "simplified" }
      ]
    },{
      featureType: "road",
      elementType: "labels",
      stylers: [
        { visibility: "off" }
      ]
    }
  ];

  // Create a new StyledMapType object, passing it the array of styles,
  // as well as the name to be displayed on the map type control.
  var styledMap = new google.maps.StyledMapType(styles,
    {name: "Styled Map"});

  // Create a map object, and include the MapTypeId to add
  // to the map type control.
  var mapOptions = {
  	center: {lat: 36.162021, lng: -86.781757},
    	zoom: 11,
	mapTypeControlOptions: {
	mapTypeIds: [google.maps.MapTypeId.ROADMAP, 'map_style']
    }
  };
  map = new google.maps.Map(document.getElementById('map'),
    mapOptions);

  //Associate the styled map with the MapTypeId and set it to display.
  map.mapTypes.set('map_style', styledMap);
  map.setMapTypeId('map_style');
  // var ddd = [36.21044921875, -86.73342895507812];
  // update_vehicle_location(ddd);

}

var array_path=[];
var array_stop = [];
function clear_map() {
	for (var i in array_path) {
		array_path[i].setMap(null);
	}
	for (var i in array_stop) {
		array_stop[i].setMap(null);
	}
}

var old_vehicle_marker=null;

function update_vehicle_location(data) {
	if (old_vehicle_marker)
		old_vehicle_marker.setMap(null);
	var myLatLng = {
		lat: data[0],
		lng: data[1],
	};
	var bus_marker = {
		url: './static/img/bus_marker.png',
		size: new google.maps.Size(50, 75),
		origin: new google.maps.Point(0, 0),
		anchor: new google.maps.Point(10, 30),
		scaledSize: new google.maps.Size(20, 30)
	};
	var marker = new google.maps.Marker({
		position: myLatLng,
		map: map,
		icon: bus_marker,
		title: ""
	});
	array_stop.push(marker);
	old_vehicle_marker = marker;
	// console.log("update_vehicle_location");
}


function draw_stops(stops) {
	console.log(stops);
	var bounds = new google.maps.LatLngBounds();
	var flag = false;
	for (var index_stop in stops) {
		flag = true;
		var myLatLng = {
			lat: stops[index_stop][0],
			lng: stops[index_stop][1],
		};
		var markerSize = 10;

		var stop_marker = {
		url: './static/img/yellowmarker.png',
		size: new google.maps.Size(50, 50),
		origin: new google.maps.Point(0, 0),
		anchor: new google.maps.Point(markerSize / 2, markerSize / 2),
		scaledSize: new google.maps.Size(markerSize, markerSize)
		};
		var marker = new google.maps.Marker({
			position: myLatLng,
			map: map,
			icon: stop_marker,
			title: ""
		});
		array_stop.push(marker);
		bounds.extend(new google.maps.LatLng(myLatLng.lat, myLatLng.lng));
	}
	if (flag) map.fitBounds(bounds);
}

function draw_all_route_segments(data) {
	clear_map();
	var routeColors = ["#3366cc", "#dc3912", "#ff9900", "#109618", "#990099", "#0099c6", "#dd4477", "#66aa00", "#b82e2e", "#316395", "#994499", "#22aa99", "#aaaa11", "#6633cc", "#e67300", "#8b0707", "#651067", "#329262", "#5574a6", "#3b3eac"];
	var bounds = new google.maps.LatLngBounds();
	for (var segment_index in data) {
		var segment_coordinates = [];
		for (var coor_index in data[segment_index]) {
			var lat_value = data[segment_index][coor_index][0];
			var lng_value = data[segment_index][coor_index][1];
			segment_coordinates.push({
				lat: lat_value,
				lng: lng_value,
			});
			bounds.extend(new google.maps.LatLng(lat_value, lng_value));
		}
		var path = new google.maps.Polyline({
	            path: segment_coordinates,
	            geodesic: true,
	            strokeColor: routeColors[segment_index % routeColors.length],
	            strokeOpacity: 0.5,
	            strokeWeight: 3
	        });
		path.setMap(map);
		array_path.push(path);
		// map.fitBounds(bounds);
	}
}

function draw_heatmap(data, performance) {
	clear_map();
	// var routeColors = ["#ff0000", "#ff3300", "#ff6600", "#ff9900", "#ffcc00", "#ffff00", "#ccff00", "#99ff00", "#66ff00", "#33ff00"];
	var routeColors = ["#ff3300", "#ff3300", "#ff3300", "#ff3300", "#ff6600", "#ff6600", "#ff9900", "#ffff00", "#99ff00", "#33ff00"];
	var bounds = new google.maps.LatLngBounds();
	for (var segment_index in data) {
		var segment_coordinates = [];
		for (var coor_index in data[segment_index]) {
			var lat_value = data[segment_index][coor_index][0];
			var lng_value = data[segment_index][coor_index][1];
			segment_coordinates.push({
				lat: lat_value,
				lng: lng_value,
			});
			bounds.extend(new google.maps.LatLng(lat_value, lng_value));
		}
		color_index = Math.floor(performance[segment_index]/10);
		var path = new google.maps.Polyline({
	            path: segment_coordinates,
	            geodesic: true,
	            strokeColor: routeColors[color_index],
	            strokeOpacity: 0.9,
	            strokeWeight: 4
	        });
		path.setMap(map);
		array_path.push(path);
		// map.fitBounds(bounds);
	}
}

var selected_route = null;
var selected_direction = null;

function map_dropdown_selected(data, selected) {
	clearTimeout(vehicle_location_timer);
	$("#dropbtn-map").html(data);
	// if ($("#dropdown-direction").outerHTML())
	socket.emit('get_map_routes', {
                selected: selected
        });
}

function route_dropdown_selected(data) {
	clearTimeout(vehicle_location_timer);
	selected_route = ""+data;
	$("#dropbtn-route").html(data);
	$("#dropbtn-direction").html("");
	$("#dropbtn-departuretime").html("");
	// if ($("#dropdown-direction").outerHTML())
	socket.emit('get_directions_for_routeid', {
                route_id: data
        });
}

function direction_dropdown_selected(data) {
	clearTimeout(vehicle_location_timer);
	selected_direction = ""+data
	$("#dropbtn-direction").html(data);
	$("#dropbtn-departuretime").html("");

	socket.emit('get_trips_for_routeid_direction', {
                route_id: selected_route,
                trip_headsign: selected_direction
        });
}



function trip_dropdown_selected(trip, departuretime) {
	clearTimeout(vehicle_location_timer);
	$("#dropbtn-departuretime").html(departuretime);

	socket.emit('get_predictions_for_trip', {
		trip_id: trip
        });

	socket.emit('get_vehicle_location_for_trip', {
		trip_id: trip
	});

	vehicle_location_timer = setInterval(function testtt() {
		socket.emit('get_vehicle_location_for_trip', {
	                trip_id: trip
	        });
	}, 30000);
}

function update_trip_dropdown(trips, departuretimes) {
	clearTimeout(vehicle_location_timer);
	$("#dropbtn-departuretime").html("");

	$("#dropdown-departuretime").html("");
	for (index in departuretimes) {
		$("#dropdown-departuretime").append("<a href='javascript:void(0);' onclick='trip_dropdown_selected(\""+trips[index]+"\",\""+departuretimes[index]+"\")'>"+departuretimes[index]+"</a>");
	}
}
	

function update_direction_dropdown(data) {
	clearTimeout(vehicle_location_timer);
	$("#dropbtn-direction").html("");
	$("#dropbtn-departuretime").html("");

	// $("#dropdown-route").html("");
	$("#dropdown-direction").html("");
	$("#dropdown-departuretime").html("");
	for (index in data) {
		$("#dropdown-direction").append("<a href='javascript:void(0);' onclick='direction_dropdown_selected(\""+data[index]+"\")'>"+data[index]+"</a>");
	}
}

function update_route_dropdown(data) {
	clearTimeout(vehicle_location_timer);
	$("#dropbtn-route").html("");
	$("#dropbtn-direction").html("");
	$("#dropbtn-departuretime").html("");

	$("#dropdown-route").html("");
	$("#dropdown-direction").html("");
	$("#dropdown-departuretime").html("");
	for (index in data) {
		$("#dropdown-route").append("<a href='javascript:void(0);' onclick='route_dropdown_selected("+data[index]+")'>"+data[index]+"</a>");
	}
}