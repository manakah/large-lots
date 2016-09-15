var geocoder = new google.maps.Geocoder();

var LargeLots = LargeLots || {};
var LargeLots = {
  map: null,
  lastClickedLayer: null,
  geojson: null,
  marker: null,
  locationScope: 'Chicago',

  initialize: function(init_params) {
      LargeLots.defaultZoom = init_params.defaultZoom;
      LargeLots.map_centroid = init_params.map_centroid;
      LargeLots.boundaryCartocss = init_params.boundaryCartocss;
      LargeLots.parcelsCartocss = init_params.parcelsCartocss;
      LargeLots.tableName = init_params.tableName;
      LargeLots.overlayName = init_params.overlayName;
      LargeLots.mainWhere = init_params.mainWhere;
      LargeLots.fields = init_params.fields;
      if (!LargeLots.map) {
        LargeLots.map = L.map('map', {
          center: LargeLots.map_centroid,
          zoom: LargeLots.defaultZoom,
          scrollWheelZoom: false
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

      LargeLots.info = L.control({position: 'bottomright'});

      LargeLots.info.onAdd = function (map) {
          this._div = L.DomUtil.create('div', 'info'); // create a div with a class "info"
          this.update();
          return this._div;
      };

      // method that we will use to update the control based on feature properties passed
      LargeLots.info.update = function (props) {
        var date_formatted = '';
        if (props) {
          var info = "<h4>" + LargeLots.formatAddress(props) + "</h4>";
          info += "<p>PIN: " + LargeLots.formatPin(props.pin14) + "<br />";
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

      LargeLots.info.clear = function(){
          this._div.innerHTML = '';
      }

      LargeLots.info.addTo(LargeLots.map);
      // We'll need to add a status column
      var fields = LargeLots.fields;
      var layerOpts = {}
      var mainSQL = 'select * from ' + LargeLots.tableName;
      if (LargeLots.mainWhere){
          mainSQL = mainSQL + LargeLots.mainWhere;
      }
      var layerOpts = {
          user_name: 'datamade',
          type: 'cartodb',
          cartodb_logo: false,
          sublayers: [{
                  sql: mainSQL,
                  cartocss: LargeLots.parcelsCartocss,
                  interactivity: fields
              },
              {
                  sql: 'select * from ' + LargeLots.overlayName,
                  cartocss: LargeLots.boundaryCartocss
              }]
      }
      cartodb.createLayer(LargeLots.map, layerOpts, { https: true })
        .addTo(LargeLots.map)
        .done(function(layer) {
            LargeLots.lotsLayer = layer.getSubLayer(0)
            LargeLots.lotsLayer.setInteraction(true);
            LargeLots.lotsLayer.on('featureOver', function(e, latlng, pos, data, subLayerIndex) {
              $('#map div').css('cursor','pointer');
              LargeLots.info.update(data);
            });
            LargeLots.lotsLayer.on('featureOut', function(e, latlng, pos, data, subLayerIndex) {
              $('#map div').css('cursor','inherit');
              LargeLots.info.clear();
            });
            LargeLots.lotsLayer.on('featureClick', function(e, pos, latlng, data){
                LargeLots.getOneParcel(data['pin14']);
                        window.setTimeout(function(){
                if($.address.parameter('pin')){
                    LargeLots.getOneParcel($.address.parameter('pin'))
                }
            }, 1000)
        }).error(function(e) {
            console.log('ERROR')
            console.log(e)
      });
      $("#search_address").val(LargeLots.convertToPlainString($.address.parameter('address')));
      LargeLots.addressSearch();
      $('.toggle-parcels').on('click', function(e){
          if($(e.target).is(':checked')){
              $(e.target).prop('checked', true)
          } else {
              $(e.target).prop('checked', false);
          }
          LargeLots.toggleParcels()
      })
  },

  toggleParcels: function(){
      var checks = []
      $.each($('.toggle-parcels'), function(i, box){
          if($(box).is(':checked')){
              checks.push($(box).attr('data-type'))
          }
      });
      var sql = 'select * from ' + LargeLots.tableName + ' where ';
      var clauses = []
      if(checks.indexOf('sold') >= 0){
          clauses.push('status = 3')
      }
      if(checks.indexOf('applied') >= 0){
          clauses.push('status = 2')
      }
      if(checks.indexOf('received') >= 0){
          clauses.push('status = 1')
      }
      if(checks.indexOf('available') >= 0){
          clauses.push('status = 0')
      }
      if(clauses.length > 0){
          clauses = clauses.join(' or ');
          sql += clauses;
      } else {
          sql = 'select * from ' + LargeLots.tableName + ' where false'
      }

      LargeLots.lotsLayer.setSQL(sql);
  },

  checkZone: function (ZONING_CLA, value) {
    if (ZONING_CLA.indexOf(value) != -1)
      return true;
    else
      return false;
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
  },

  getOneParcel: function(pin14){
      if (LargeLots.lastClickedLayer){
        LargeLots.map.removeLayer(LargeLots.lastClickedLayer);
      }
      var sql = new cartodb.SQL({user: 'datamade', format: 'geojson'});
      sql.execute("select * from {{table}} where pin14 = '{{pin14}}'", {table:LargeLots.tableName, pin14:pin14})
        .done(function(data){
            var shape = data.features[0];
            LargeLots.lastClickedLayer = L.geoJson(shape);
            LargeLots.lastClickedLayer.addTo(LargeLots.map);
            LargeLots.lastClickedLayer.setStyle({fillColor:'#f7fcb9', weight: 2, fillOpacity: 1, color: '#000'});
            LargeLots.map.setView(LargeLots.lastClickedLayer.getBounds().getCenter(), 17);
            LargeLots.selectParcel(shape.properties);
        });
  },

  selectParcel: function (props){
      var address = LargeLots.formatAddress(props);
      var zoning = LargeLots.getZoning(props.zoning_classification);
      var status = 'Not applied for';
      var status_class = 'available';
      if (props.status == 1){
          status = 'Application received';
          status_class = 'applied';
      }
      if (props.status == 2){
          status = 'Application approved';
          status_class = 'applied';
      }
      if (props.status == 3){
          status = 'Sold!';
          status_class = 'applied';
      }
      var info = "<p>Selected lot: </p><img class='img-responsive img-thumbnail' src='https://pic.datamade.us/" + props.pin14 + ".jpg' />\
        <table class='table table-bordered table-condensed'><tbody>\
          <tr><td>Address</td><td>" + address + "</td></tr>\
          <tr><td>PIN</td><td>" + LargeLots.formatPin(props.pin14) + "</td></tr>\
          <tr><td>&nbsp;</td><td><a target='_blank' href='http://cookcountypropertyinfo.com/Pages/PIN-Results.aspx?PIN=" + props.pin14 + "'>Tax and deed history &raquo;</a></td></tr>\
          <tr><td>Zoned</td><td> Residential (<a href='http://secondcityzoning.org/zone/" + props.zoning_classification + "' target='_blank'>" + props.zoning_classification + "</a>)</td></tr>\
          <tr><td>Sq ft</td><td>" + props.sq_ft + "</td></tr>\
          <tr><td>Status</td><td><span class='label label-" + status_class + "'>" + status + "</span></td></tr>\
        </tbody></table>";
      $.address.parameter('pin', props.pin14)
      $('#lot-info').html(info);
  },

  getZoning: function(code){
      var zone_type = code.split('-')[0];
      var text = '';
      if (zone_type == 'RS'){
          text = 'Single family home'
      }
      if (zone_type == 'RT'){
          text = 'Two-flat, townhouse'
      }
      if (zone_type == 'RM'){
          text = 'Medium-density apartment'
      }
      return text;
  },

  addressSearch: function (e) {
    if (e) e.preventDefault();
    var searchAddress = $("#search_address").val();
    if (searchAddress != '') {

      $("#id_owned_address").val(searchAddress.replace((", " + LargeLots.locationScope), ""));

      if(LargeLots.locationScope && LargeLots.locationScope.length){
        var checkaddress = searchAddress.toLowerCase();
        var checkcity = LargeLots.locationScope.split(",")[0].toLowerCase();
        if(checkaddress.indexOf(checkcity) == -1){
          searchAddress += ", " + LargeLots.locationScope;
        }
      }

      $.address.parameter('address', encodeURIComponent(searchAddress));

      geocoder.geocode( { 'address': searchAddress}, function(results, status) {
        if (status == google.maps.GeocoderStatus.OK) {
          currentPinpoint = [results[0].geometry.location.lat(), results[0].geometry.location.lng()];

          // check if the point is in neighborhood area
          var sql = new cartodb.SQL({user: 'datamade', format: 'geojson'});
          sql.execute("select cartodb_id, the_geom FROM " + LargeLots.overlayName + " AND ST_Intersects( the_geom, ST_SetSRID(ST_POINT({{lng}}, {{lat}}) , 4326))", {lng:currentPinpoint[1], lat:currentPinpoint[0]})
          .done(function(data){
            if (data.features.length == 0) {
              alert("Your address is outside the program area. Please try again.");
            }
            else {
              LargeLots.map.setView(currentPinpoint, 17);

              if (LargeLots.marker)
                LargeLots.map.removeLayer( LargeLots.marker );

              LargeLots.marker = L.marker(currentPinpoint).addTo(LargeLots.map);
            }

          }).error(function(e){console.log(e)});
        }
        else {
          alert("We could not find your address: " + status);
        }
      });
    }
  },

  formatPin: function(pin) {
    pin = pin + '';
    return pin.replace(/(\d{2})(\d{2})(\d{3})(\d{3})(\d{4})/, '$1-$2-$3-$4-$5');
  },

  //converts a slug or query string in to readable text
  convertToPlainString: function (text) {
    if (text == undefined) return '';
    return decodeURIComponent(text);
  }

}
