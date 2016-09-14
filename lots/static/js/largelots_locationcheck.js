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
  cartodb_table: 'ag_lots',

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
          info += "<h5>Property owned by applicant</h5>"
          info += "<p>PIN: " + LargeLots.formatPin(props.display_pin) + "<br />";
          info += "Zoned: " + props.zoning_classification + "<br />";
          info += "Sq Ft: " + props.sq_ft + "<p/>";
          this._div.innerHTML  = info;
        }
      };

      LargeLots.infoOwned.addTo(LargeLots.map);

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
          info += "<h5>Property for sale</h5>"
          info += "<p>PIN: " + LargeLots.formatPin(props.display_pin) + "<br />";
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

      LargeLots.clear = function(infoDiv) {
        infoDiv._div.innerHTML = '';
      }

      LargeLots.infoApplied.addTo(LargeLots.map);

      var sqlOwned = "select * from " + LargeLots.cartodb_table + " where pin14='" + ownedPin + "'";
      var sqlApplied = " select * from " + LargeLots.cartodb_table + " where pin14='0000000000'"
      $.each(appliedPins, function(i, pin) {
        sqlApplied += " or pin14='" + pin + "'"
      })

      var fields = "display_pin,zoning_classification,ward,street_name,street_dir,street_number,street_type,city_owned,residential"
      var layerOpts = {
          user_name: 'datamade',
          type: 'cartodb',
          cartodb_logo: false,
          sublayers: [
              {
                  sql: sqlOwned,
                  cartocss: $('#owned-styles').html().trim(),
                  interactivity: fields
              },
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

            var appliedProperty = layer.getSubLayer(1);
            appliedProperty.setInteraction(true);
            appliedProperty.on('featureOver', function(e, latlng, pos, data, subLayerIndex) {
              $('#locationcheck-map div').css('cursor','pointer');
              LargeLots.infoApplied.update(data);
            });
            appliedProperty.on('featureOut', function(e, latlng, pos, data, subLayerIndex) {
              $('#locationcheck-map div').css('cursor','inherit');
              LargeLots.clear(LargeLots.infoApplied);
            });

            $.each(appliedPins, function(i, pin) {
              sqlOwned += " or pin14='" + pin + "'"
            });

            var sqlBounds = new cartodb.SQL({ user: 'datamade' });
            sqlBounds.getBounds(sqlOwned).done(function(bounds){
              LargeLots.map.fitBounds(bounds);
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
    if (prop.street_number == null) prop.street_number = "";
    if (prop.street_dir == null) prop.street_dir = "";
    if (prop.street_name == null) prop.street_name = "";

    var ret = prop.street_number + " " + prop.street_dir + " " + prop.street_name + " " + prop.street_type;
    if (ret.trim() == "")
      return "Unknown";
    else
      return ret;
  }

}