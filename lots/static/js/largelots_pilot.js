var geocoder = new google.maps.Geocoder();

var LargeLots = LargeLots || {};
var LargeLots = {

  map: null,
  map_centroid: [41.7872, -87.6345],
  defaultZoom: 11,
  lastClickedLayer: null,
  geojson: null,
  marker: null,
  locationScope: 'chicago',
  cartodb_table: 'large_lots_citywide_expansion_data',

  initialize: function() {

      if (!LargeLots.map) {
        LargeLots.map = L.map('map', {
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
          var info = '';
          if(props.street_number){
              info += "<h4>" + LargeLots.formatAddress(props) + "</h4>";
              info += "<p>PIN: " + props.pin_nbr + "<br />";
          }
          // if (props.zoning_classification){
          //     info += "Zoned: " + props.zoning_classification + "<br />";
          // }
          // if (props.sq_ft){
          //     info += "Sq Ft: " + props.sq_ft + "<br />";
          // }
          this._div.innerHTML  = info;
        }
      };

      LargeLots.info.clear = function(){
          this._div.innerHTML = '';
      }

      LargeLots.info.addTo(LargeLots.map);

      var fields = "pin, pin_nbr, street_name, street_direction, street_type, city_owned_ind, residential"
      var layerOpts = {
          user_name: 'datamade',
          type: 'cartodb',
          cartodb_logo: false,
          sublayers: [
              {
                  sql: "select * from " + LargeLots.cartodb_table,
                  cartocss: $('#map-styles').html().trim(),
                  interactivity: fields
              },
              {
                  sql: "select * from chicago_community_areas where community = 'LARGE LOTS EXPANSION'",
                  cartocss: "#" + LargeLots.cartodb_table + "{polygon-fill: #ffffcc;polygon-opacity: 0.25;line-color: #FFF;line-width: 3;line-opacity: 1;}"
              }
          ]
      }
      cartodb.createLayer(LargeLots.map, layerOpts, { https: true })
        .addTo(LargeLots.map)
        .done(function(layer) {
            LargeLots.lotsLayer = layer.getSubLayer(0);
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
                LargeLots.getOneParcel(data['pin_nbr']);
            });
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
              checks.push($(box).attr('id'))
          }
      });
      var sql = 'select * from ' + LargeLots.cartodb_table;
      var clauses = []
      if(checks.indexOf('applied') >= 0){
          clauses.push('status = 1')
      }
      if(checks.indexOf('available') >= 0){
          clauses.push('status = 0')
      }
      if(clauses.length > 0){
          clauses = clauses.join(' or ');
          sql += clauses;
      } else {
          sql = 'select * from ' + LargeLots.cartodb_table;
      }
      LargeLots.lotsLayer.setSQL(sql);
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

  getOneParcel: function(pin_nbr){
      if (LargeLots.lastClickedLayer){
        LargeLots.map.removeLayer(LargeLots.lastClickedLayer);
      }
      var sql = new cartodb.SQL({user: 'datamade', format: 'geojson'});
      sql.execute('select * from ' + LargeLots.cartodb_table + ' where pin_nbr = {{pin_nbr}}::VARCHAR', {pin_nbr:pin_nbr})
        .done(function(data){
            var shape = data.features[0];
            LargeLots.lastClickedLayer = L.geoJson(shape);
            LargeLots.lastClickedLayer.addTo(LargeLots.map);
            LargeLots.lastClickedLayer.setStyle({fillColor:'#f7fcb9', weight: 2, fillOpacity: 1, color: '#000'});
            LargeLots.map.setView(LargeLots.lastClickedLayer.getBounds().getCenter(), 17);
            LargeLots.selectParcel(shape.properties);
        }).error(function(e){console.log(e)});
      window.location.hash = 'browse';
  },

  selectParcel: function (props){
      // console.log(props)
      var address = LargeLots.formatAddress(props);
      var pin_formatted = LargeLots.formatPin(props.pin_nbr);

      var info = "<div class='row'><div class='col-xs-6 col-md-12'>\
        <table class='table table-bordered table-condensed'><tbody>\
          <tr><td>Address</td><td>" + address + "</td></tr>\
          <tr><td>PIN</td><td>" + pin_formatted + " (<a target='_blank' href='http://www.cookcountypropertyinfo.com/cookviewerpinresults.aspx?pin=" + props.pin_nbr + "'>info</a>)</td></tr>";
      if (props.zoning_classification){
          info += "<tr><td>Zoned</td><td> Residential (<a href='http://secondcityzoning.org/zone/" + props.zoning_classification + "' target='_blank'>" + props.zoning_classification + "</a>)</td></tr>";
      }
      if (props.sq_ft){
          info += "<tr><td>Sq ft</td><td>" + LargeLots.addCommas(Math.floor(props.sq_ft)) + "</td></tr>";

      }
      info += "<tr><td colspan='2'><button type='button' id='lot_apply' data-pin='" + pin_formatted + "' data-address='" + address + "' href='#' class='btn btn-success'>Select this lot</button></td></tr>"
      info += "</tbody></table></div><div class='col-xs-6 col-md-12'>\
      <img class='img-responsive img-thumbnail' src='https://pic.datamade.us/" + props.pin_nbr + ".jpg' /></div></div>";
      $.address.parameter('pin', props.pin_nbr)
      $('#lot-info').html(info);
      // console.log(info)

      $("#lot_apply").on("click", function(){
        if ($("#id_lot_1_pin").val() == "") {
          $("#id_lot_1_address").val($(this).data('address'));
          $("#id_lot_1_pin").val($(this).data('pin'));
        }
        else if ($("#id_lot_1_pin").val() != $(this).data('pin')){
          $("#id_lot_2_address").val($(this).data('address'));
          $("#id_lot_2_pin").val($(this).data('pin'));
        }

        $(this).html("<i class='fa fa-check'></i> Selected");
        $("#selected_lots").ScrollTo({offsetTop: "70px", 'axis':'y'});
      });
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
          sql.execute("select cartodb_id, the_geom FROM chicago_community_areas WHERE community = 'LARGE LOTS EXPANSION' AND ST_Intersects( the_geom, ST_SetSRID(ST_POINT({{lng}}, {{lat}}) , 4326))", {lng:currentPinpoint[1], lat:currentPinpoint[0]})
          .done(function(data){
            // console.log(data);
            if (data.features.length == 0) {
              $('#addr_search_modal').html(LargeLots.convertToPlainString($.address.parameter('address')));
              $('#modalGeocode').modal('show');
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
    var pin  = String(pin);
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
