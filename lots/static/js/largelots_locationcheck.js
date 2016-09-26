var geocoder = new google.maps.Geocoder();

var LargeLots = LargeLots || {};
var LargeLots = {
  map: null,
  map_centroid: [41.7442054377053, -87.6563067873806],
  defaultZoom: 14,
  lastClickedLayer: null,
  geojson: null,
  marker: null,
  locationScope: 'chicago',
  // cartodb_table: 'large_lots_citywide_test',
  cartodb_table: 'large_lots_citywide_expansion_data',

  initialize: function() {

      if (!LargeLots.map) {
        LargeLots.map = L.map('locationcheck-map', {
          center: LargeLots.map_centroid,
          zoom: LargeLots.defaultZoom,
          scrollWheelZoom: false,
          tapTolerance: 30
        });
      }
      // render a map!
      L.Icon.Default.imagePath = '/static/images/'

      var google_map_styles = [
        {
          stylers: [
            { saturation: -100 },
            { lightness: 40 }
          ]
        }
      ];

      var layer = new L.Google('ROADMAP', {mapOptions: {styles: google_map_styles}});
      LargeLots.map.addLayer(layer);

      // info div for application property
      LargeLots.infoApplied = L.control({position: 'bottomright'});

      LargeLots.infoApplied.onAdd = function (map) {
          this._div = L.DomUtil.create('div', 'infoApplied');
          this.update();
          return this._div;
      };

      LargeLots.infoApplied.update = function (props) {
        var date_formatted = '';
        if (props) {
          var info = "<h4>" + LargeLots.formatAddress(props) + "</h4>";
          info += "<h5>Lot for sale</h5>"
          info += "<p>PIN: " + LargeLots.formatPin(props.pin_nbr) + "<br />";
          info += "Ward: " + props.ward + "<br />";
          info += "Zoned: " + props.zone_class + "<br />";
          info += "Sq Ft: " + Math.floor(props.square_feet) + "<br />";
          info += "</p>"

          this._div.innerHTML  = info;
        }
      };

      LargeLots.infoApplied.addTo(LargeLots.map);

      LargeLots.clear = function(infoDiv) {
        infoDiv._div.innerHTML = '';
      }


      // info div for owned property
      LargeLots.infoOwned = L.control({position: 'bottomright'});

      LargeLots.infoOwned.onAdd = function (map) {
          this._div = L.DomUtil.create('div', 'infoOwned');
          this.update();
          return this._div;
      };

      LargeLots.infoOwned.update = function (props) {
        var date_formatted = '';
        if (props) {
          var info = "<h4>" + props.Address + "</h4>";
          info += "<h5>Property owned by the applicant</h5>"
          info += "<p>PIN: " + LargeLots.formatPin(props.PIN14) + "<br />";
          info += "Sq Ft: " + props.LandSqft + "<p/>";
          this._div.innerHTML  = info;
        }
      };

      LargeLots.infoOwned.addTo(LargeLots.map);


      // info div for other applicants' properties
      LargeLots.infoOtherApplicants = L.control({position: 'bottomright'});

      LargeLots.infoOtherApplicants.onAdd = function (map) {
          this._div = L.DomUtil.create('div', 'infoOtherApplicants');
          this.update();
          return this._div;
      };

      LargeLots.infoOtherApplicants.update = function (props) {
        var date_formatted = '';
        if (props) {
          var info = "<h4>" + props.Address + "</h4>";
          info += "<h5>Property owned by another applicant</h5>"
          info += "<p>PIN: " + LargeLots.formatPin(props.PIN14) + "<br />";
          info += "Sq Ft: " + props.LandSqft + "<p/>";
          this._div.innerHTML  = info;
        }
      };

      LargeLots.infoOtherApplicants.addTo(LargeLots.map);


      // Add legend.
      LargeLots.locationsLegend = L.control({position: 'bottomleft'});

      LargeLots.locationsLegend.onAdd = function (map) {
          this._div = L.DomUtil.create('div', 'locationsLegend');
          this._div.innerHTML = '<ul class="location-legend">' +
          '<li><div id="sale-lot" class="legend-block"></div><div class="legend-block text">Lot for sale</div></li>' +
          '<li><div id="owned-prop" class="legend-block"></div><div class="legend-block text">Owned by applicant<div></li>' +
          '<li><div id="other-prop" class="legend-block"></div><div class="legend-block text">Owned by other applicants</div></li></ul>'
          return this._div;
      };
      LargeLots.locationsLegend.addTo(LargeLots.map);

      var sqlApplied = "select * from " + LargeLots.cartodb_table + " where pin_nbr='" + lotPin + "'";

      var fields = "pin, pin_nbr, street_name, street_direction, street_type, ward, square_feet, zone_class"
      var layerOpts = {
          user_name: 'datamade',
          type: 'cartodb',
          cartodb_logo: false,
          sublayers: [
              {
                  sql: sqlApplied,
                  cartocss: $('#applied-styles').html().trim(),
                  interactivity: fields
              }
          ]
      }
      cartodb.createLayer(LargeLots.map, layerOpts)
        .addTo(LargeLots.map)
        .done(function(layer) {
            // Make a sublayer for the applicant's owned property
            var appliedProperty = layer.getSubLayer(0);
            appliedProperty.setInteraction(true);
            appliedProperty.on('featureOver', function(e, latlng, pos, data, subLayerIndex) {
              $('#locationcheck-map div').css('cursor','pointer');
              LargeLots.infoApplied.update(data);
            });
            appliedProperty.on('featureOut', function(e, latlng, pos, data, subLayerIndex) {
              $('#locationcheck-map div').css('cursor','inherit');
              LargeLots.clear(LargeLots.infoApplied);
            });

            var sqlBounds = new cartodb.SQL({ user: 'datamade' });
            sqlBounds.getBounds(sqlApplied).done(function(bounds){
              LargeLots.map.fitBounds(bounds);
              LargeLots.map.setZoom(18);
            });
        }).error(function(e) {
        console.log('ERROR')
        console.log(e)
      });


      //fetch the applicant's lot geometry based on their pin
      $.when($.get('/get-parcel-geometry/?pin=' + ownedPin)).then(
        function(ownedParcel){
          L.geoJson(ownedParcel, {
              style: {"fillColor": "#A1285D", "fillOpacity": 0.7, "color": "#A1285D", 'opacity': 1, 'weight': 1},
              onEachFeature: function(feature, layer) {
                console.log(feature.properties);
                layer.on('mouseover', function() {
                  LargeLots.infoOwned.update(feature.properties);
                });
                layer.on('mouseout', function() {
                  LargeLots.clear(LargeLots.infoOwned);
                });
              }
          }).addTo(LargeLots.map);
      });

      //for everyone else who applied to the lot, fetch their property geometry based on their pin
      $.each(otherOwnedPins, function(i, pin){
        $.when($.get('/get-parcel-geometry/?pin=' + pin)).then(
          function(otherOwnedParcel){
            L.geoJson(otherOwnedParcel, {
                style: {"fillColor": "#A1285D", "fillOpacity": 0.2, "color": "#A1285D", 'opacity': 1, 'weight': 1},
                onEachFeature: function(feature, layer) {
                  layer.on('mouseover', function() {
                    LargeLots.infoOtherApplicants.update(feature.properties);
                  });
                  layer.on('mouseout', function() {
                    LargeLots.clear(LargeLots.infoOtherApplicants);
                  });
                }
            }).addTo(LargeLots.map);
        });
      });

  },

  formatPin: function(pin) {
    pin = pin + '';
    return pin.replace(/(\d{2})(\d{2})(\d{3})(\d{3})(\d{4})/, '$1-$2-$3-$4-$5');
  },

  formatAddress: function (prop) {
    if (prop.street_type == null) prop.street_type = "";
    if (prop.low_address == null) prop.low_address = "";
    if (prop.street_direction == null) prop.street_direction = "";
    if (prop.street_name == null) prop.street_name = "";

    var ret = prop.low_address + " " + prop.street_direction + " " + prop.street_name + " " + prop.street_type;
    if (ret.trim() == "")
      return "Unknown";
    else
      return ret;
  }

}