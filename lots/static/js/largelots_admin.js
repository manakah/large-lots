var LargeLotsAdmin = LargeLotsAdmin || {};
var LargeLotsAdmin = {

  map: null,
  map_centroid: [41.7872, -87.6345],
  defaultZoom: 11,
  lastClickedLayer: null,
  geojson: null,
  marker: null,
  locationScope: 'chicago',
  cartodb_table: 'large_lots_citywide_expansion_data',

  initialize: function() {

      if (!LargeLotsAdmin.map) {
        LargeLotsAdmin.map = L.map('map-admin', {
          center: LargeLotsAdmin.map_centroid,
          zoom: LargeLotsAdmin.defaultZoom,
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

      var layer = new L.Google('ROADMAP', {mapOptions: {styles: google_map_styles}
      });
      LargeLotsAdmin.map.addLayer(layer);

      LargeLotsAdmin.info = L.control({position: 'bottomright'});

      LargeLotsAdmin.info.onAdd = function (map) {
          this._div = L.DomUtil.create('div', 'mapInfo'); // create a div with a class "info"
          this.update();
          return this._div;
      };

      // Info box: method that we will use to update the control based on feature properties passed
      var fields = "pin, pin_nbr, street_name, street_direction, street_type, ward, square_feet, zone_class, community"

      LargeLotsAdmin.info.update = function (props) {
        var date_formatted = '';
        if (props) {
          var info = '';
          if(props.street_name){
              info += "<h4>" + LargeLotsAdmin.formatAddress(props) + "</h4>";
              info += "<p><strong>PIN: " + props.pin + "</strong></p>";
              info += "Community: " + props.community + "<br />";
              info += "Ward: " + props.ward + "<br />";
          }
          if (props.square_feet){
              info += "Sq Ft: " + Math.floor(props.square_feet) + "<br />";
          }
          this._div.innerHTML  = info;
        }
      };

      LargeLotsAdmin.info.clear = function(){
          this._div.innerHTML = '';
      }

      LargeLotsAdmin.info.addTo(LargeLotsAdmin.map);

      var layerOpts = {
          user_name: 'datamade',
          type: 'cartodb',
          cartodb_logo: false,
          sublayers: [

              {
                  sql: "select * from large_lots_citywide_expansion_data",
                  cartocss: $('#egp-styles').html().trim(),
                  interactivity: fields
              },
              {
                  sql: "select * from large_lots_citywide_expansion_data where pin_nbr in (" + applied_pins + ")",
                  cartocss: $('#egp-styles-applied').html().trim(),
                  interactivity: fields
              },
              {
                  sql: "select * from chicago_community_areas where community = 'LARGE LOTS EXPANSION'",
                  cartocss: "#" + LargeLotsAdmin.cartodb_table + "{polygon-fill: #ffffcc;polygon-opacity: 0.25;line-color: #FFF;line-width: 3;line-opacity: 1;}"
              }
          ]
      }
      cartodb.createLayer(LargeLotsAdmin.map, layerOpts)
        .addTo(LargeLotsAdmin.map)
        .done(function(layer) {
            LargeLotsAdmin.lotsLayer = layer.getSubLayer(0);
            LargeLotsAdmin.lotsLayer.setInteraction(true);

            LargeLotsAdmin.lotsLayer.on('featureOver', function(e, latlng, pos, data, subLayerIndex) {
              $('#map-admin div').css('cursor','pointer');
              LargeLotsAdmin.info.update(data);
            });
            LargeLotsAdmin.lotsLayer.on('featureOut', function(e, latlng, pos, data, subLayerIndex) {
              $('#map-admin div').css('cursor','inherit');
              LargeLotsAdmin.info.clear();
            });
            LargeLotsAdmin.lotsLayer.on('featureClick', function(e, pos, latlng, data){
                LargeLotsAdmin.getOneParcel(data['pin14']);
            });
        }).error(function(e) {
        //console.log('ERROR')
        //console.log(e)
      });
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
  },

  getOneParcel: function(pin14){
      if (LargeLotsAdmin.lastClickedLayer){
        LargeLotsAdmin.map.removeLayer(LargeLotsAdmin.lastClickedLayer);
      }
      var sql = new cartodb.SQL({user: 'datamade', format: 'geojson'});
      sql.execute('select * from large_lots_citywide_expansion_data where pin14 = cast({{pin14}} as text)', {pin14:pin14})
        .done(function(data){
            var shape = data.features[0];
            LargeLotsAdmin.lastClickedLayer = L.geoJson(shape);
            LargeLotsAdmin.lastClickedLayer.addTo(LargeLotsAdmin.map);
            LargeLotsAdmin.lastClickedLayer.setStyle({fillColor:'#f7fcb9', weight: 2, fillOpacity: 1, color: '#000'});
            LargeLotsAdmin.map.setView(LargeLotsAdmin.lastClickedLayer.getBounds().getCenter(), 17);
        }).error(function(e){
          console.log(e);
        });
      window.location.hash = 'browse';
  },

  formatPin: function(pin) {
    return pin.replace(/(\d{2})(\d{2})(\d{3})(\d{3})(\d{4})/, '$1-$2-$3-$4-$5');
  },

  //converts a slug or query string in to readable text
  convertToPlainString: function (text) {
    if (text == undefined) return '';
    return decodeURIComponent(text);
  },

  addCommas: function(nStr) {
    nStr += '';
    x = nStr.split('.');
    x1 = x[0];
    x2 = x.length > 1 ? '.' + x[1] : '';
    var rgx = /(\d+)(\d{3})/;
    while (rgx.test(x1)) {
      x1 = x1.replace(rgx, '$1' + ',' + '$2');
    }
    return x1 + x2;
  }

}
