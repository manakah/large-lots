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
          var info = "<h4>" + LargeLots.formatAddress(props) + "</h4>";
          info += "<h5>Property owned by the applicant</h5>"
          info += "<p>PIN: " + LargeLots.formatPin(props.pin_nbr) + "<br />";
          info += "Zoned: " + props.zoning_classification + "<br />";
          info += "Sq Ft: " + props.sq_ft + "<p/>";
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
          var info = "<h4>" + LargeLots.formatAddress(props) + "</h4>";
          info += "<h5>Property owned by another applicant</h5>"
          info += "<p>PIN: " + LargeLots.formatPin(props.pin_nbr) + "<br />";
          info += "Zoned: " + props.zoning_classification + "<br />";
          info += "Sq Ft: " + props.sq_ft + "<p/>";
          this._div.innerHTML  = info;
        }
      };

      LargeLots.infoOtherApplicants.addTo(LargeLots.map);


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
          if (props.residential == "T"){
            residential = "True"
          }
          else {
            residential = "False"
          }
          var info = "<h4>" + LargeLots.formatAddress(props) + "</h4>";
          info += "<h5>Lot for sale</h5>"
          info += "<p>PIN: " + LargeLots.formatPin(props.pin_nbr) + "<br />";
          info += "Residential: " + residential + "<br />";
          info += "Zoned: " + props.zoning_classification + "<br />";
          info += "Sq Ft: " + props.sq_ft + "<br />";
          if (props.status == 1){
            info += "Status: <strong>Application received</strong>";
          }
          else if (props.status == 2){
            info += "Status: <strong>Application approved</strong>";
          }
          else if (props.status == 3){
            info += "Status: <strong>Sold!</strong>";
          }
          else {
            info += "Status: <strong>Available</strong>";
          }
          info += "</p>"

          this._div.innerHTML  = info;
        }
      };

      LargeLots.infoApplied.addTo(LargeLots.map);

      LargeLots.clear = function(infoDiv) {
        infoDiv._div.innerHTML = '';
      }

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

      // // Make SQL queries.
      // var sqlOwned = "select * from " + LargeLots.cartodb_table + " where pin_nbr='" + ownedPin + "'";

      // // Check that applicant entered a valid pin.
      // var sql = new cartodb.SQL({ user: 'datamade' });
      // sql.execute(sqlOwned).done(function(data) {
      //   if(data.rows.length == 0) {
      //     alert("We cannot locate the applicant's property on the map, likely because the applicant did not enter a valid pin. You can deny this application by selecting 'No' or contact the applicant for clarification.")
      //   }
      // });

      var sqlApplied = "select * from " + LargeLots.cartodb_table + " where pin_nbr='" + lotPin + "'";

      // var sqlOtherApplicants = " select * from " + LargeLots.cartodb_table + " where pin_nbr='0000000000'"
      // $.each(otherOwnedPins, function(i, pin) {
      //   sqlOtherApplicants += " or pin_nbr='" + pin + "'"
      // })

      // var fields = "display_pin,zoning_classification,ward,street_name,street_dir,street_number,street_type,city_owned,residential"
      var fields = "pin, pin_nbr, street_name, street_direction, street_type, city_owned_ind, residential"
      var layerOpts = {
          user_name: 'datamade',
          type: 'cartodb',
          cartodb_logo: false,
          sublayers: [
              // {
              //     sql: sqlOwned,
              //     cartocss: $('#owned-styles').html().trim(),
              //     interactivity: fields
              // },
              {
                  sql: sqlApplied,
                  cartocss: $('#applied-styles').html().trim(),
                  interactivity: fields
              }
              // {
              //     sql: sqlOtherApplicants,
              //     cartocss: $('#other-applied-styles').html().trim(),
              //     interactivity: fields
              // },
          ]
      }
      cartodb.createLayer(LargeLots.map, layerOpts)
        .addTo(LargeLots.map)
        .done(function(layer) {
            // Make a sublayer for the applicant's owned property
            var ownedProperty = layer.getSubLayer(0);
            ownedProperty.setInteraction(true);
            ownedProperty.on('featureOver', function(e, latlng, pos, data, subLayerIndex) {
              $('#locationcheck-map div').css('cursor','pointer');
              LargeLots.infoOwned.update(data);
            });
            ownedProperty.on('featureOut', function(e, latlng, pos, data, subLayerIndex) {
              $('#locationcheck-map div').css('cursor','inherit');
              LargeLots.clear(LargeLots.infoOwned);
            });

            // // Make a sublayer for the property applied for.
            // var appliedProperty = layer.getSubLayer(1);
            // appliedProperty.setInteraction(true);
            // appliedProperty.on('featureOver', function(e, latlng, pos, data, subLayerIndex) {
            //   $('#locationcheck-map div').css('cursor','pointer');
            //   LargeLots.infoApplied.update(data);
            // });
            // appliedProperty.on('featureOut', function(e, latlng, pos, data, subLayerIndex) {
            //   $('#locationcheck-map div').css('cursor','inherit');
            //   LargeLots.clear(LargeLots.infoApplied);
            // });


            // // Make a sublayer for other applicants on the same property.
            // var otherApplicantProperties = layer.getSubLayer(2);
            // otherApplicantProperties.setInteraction(true);
            // otherApplicantProperties.on('featureOver', function(e, latlng, pos, data, subLayerIndex) {
            //   $('#locationcheck-map div').css('cursor','pointer');
            //   LargeLots.infoOtherApplicants.update(data);
            // });
            // otherApplicantProperties.on('featureOut', function(e, latlng, pos, data, subLayerIndex) {
            //   $('#locationcheck-map div').css('cursor','inherit');
            //   LargeLots.clear(LargeLots.infoOtherApplicants);
            // });

            var sqlBounds = new cartodb.SQL({ user: 'datamade' });
            sqlBounds.getBounds(sqlApplied).done(function(bounds){
              LargeLots.map.fitBounds(bounds);
              LargeLots.map.setZoom(18);
            });
        }).error(function(e) {
        console.log('ERROR')
        console.log(e)
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