var geocoder = new google.maps.Geocoder();

var LargeLots = LargeLots || {};
var LargeLots = {

  map: null,
  lastClickedLayer: null,
  geojson: null,
  marker: null,
  locationScope: 'chicago',

  initialize: function(init_params) {
      LargeLots.map_centroid = init_params.map_centroid;
      LargeLots.defaultZoom = init_params.defaultZoom;
      LargeLots.cartodb_table = init_params.cartodb_table;
      LargeLots.mainWhere = init_params.mainWhere;
      LargeLots.overlayName = init_params.overlayName;
      LargeLots.fields = init_params.fields;
      LargeLots.extra_sublayers = init_params.extra_sublayers;

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

      var layer = new L.Google('ROADMAP', {mapOptions: {styles: google_map_styles}
      });
      LargeLots.map.addLayer(layer);

      // code for info box bubble
      LargeLots.info = L.control({position: 'bottomright'});

      LargeLots.info.onAdd = function (map) {
          this._div = L.DomUtil.create('div', 'info'); // create a div with a class "info"
          this.update();
          return this._div;
      };

      // method that we will use to update the control based on feature properties passed
      LargeLots.info.update = function (props) {
        var date_formatted = '';
        var info = 'Hover over a lot to learn more';
        if (props) {
          info = '';
          if(props.street_name){
              info += "<h4>" + LargeLots.formatAddress(props) + "</h4>";
              info += "<strong>PIN: " + LargeLots.formatPin(props.pin_nbr) + "</strong><br />";
              if (props.community) {
                info += "Community: " + props.community + "<br />";
              }
              if (props.ward) {
                info += "Ward: " + props.ward + "<br />";
              }
          }
          if (props.square_feet){
              info += "Sq Ft: " + Math.floor(props.square_feet) + "<br />";
          }
        }
        this._div.innerHTML = info;
      };

      LargeLots.info.clear = function(){
          this._div.innerHTML = 'Hover over a lot to learn more';
      }

      LargeLots.info.addTo(LargeLots.map);

      var layerOpts = {
          user_name: 'datamade',
          type: 'cartodb',
          cartodb_logo: false,
          sublayers: [
              {
                  sql: "select * from " + LargeLots.cartodb_table + LargeLots.mainWhere,
                  cartocss: $('#map-styles').html().trim(),
                  interactivity: LargeLots.fields
              },
              {
                  sql: "select * from " +  LargeLots.overlayName,
                  cartocss: "#" + LargeLots.cartodb_table + "{polygon-fill: #ffffcc;polygon-opacity: 0.25;line-color: #FFF;line-width: 3;line-opacity: 1;}"
              }
          ]
      }

      if (LargeLots.extra_sublayers) {
        $.each(LargeLots.extra_sublayers, function(index, value) {
          layerOpts.sublayers.push(value)
        })
      }

      cartodb.createLayer(LargeLots.map, layerOpts, { https: true })
        .addTo(LargeLots.map)
        .done(function(layer) {
            allLayers = [];
            LargeLots.lotsLayer = layer.getSubLayer(0);
            allLayers.push(LargeLots.lotsLayer);
            
            if (LargeLots.extra_sublayers) {
              if (layer.getSubLayer(2)) {
                LargeLots.soldLotsLayer = layer.getSubLayer(2);
                allLayers.push(LargeLots.soldLotsLayer);
              }
              if (layer.getSubLayer(3)) {
                LargeLots.appliedLotsLayer = layer.getSubLayer(3);
                allLayers.push(LargeLots.appliedLotsLayer);
              }
            }

            // Set interactivity for multiple layers
            $.each(allLayers, function(index, value) {
                value.setInteraction(true);
                value.on('mouseover', function(e, latlng, pos, data, value) {
                    $('#map div').css('cursor','pointer');
                    LargeLots.info.update(data);
                });
                value.on('mouseout', function(e, latlng, pos, data, value) {
                    $('#map div').css('cursor','inherit');
                    LargeLots.info.clear();
                });
                value.on('featureClick', function(e, pos, latlng, data){
                    LargeLots.getOneParcel(data['pin_nbr']);
                });
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

      if($("#search_address").length != 0) {
        $("#search_address").val(LargeLots.convertToPlainString($.address.parameter('address')));
        LargeLots.addressSearch();
      }

      $('.toggle-parcels').on('click', function(e){
          if($(e.target).is(':checked')){
              $(e.target).prop('checked', true)
          } else {
              $(e.target).prop('checked', false);
          }
          LargeLots.toggleParcels()
      });
  },

  toggleParcels: function(){
      var checks = []
      $.each($('.toggle-parcels'), function(i, box){
          if($(box).is(':checked')){
              checks.push($(box).attr('data-type'))
          }
      });
      var sql = 'select * from ' + LargeLots.cartodb_table + ' where ';
      var clauses = []
      if(checks.indexOf('sold') >= 0){
          soldSQL = "(select cartodb_id, the_geom, the_geom_webmercator, pin, pin_nbr, street_name, street_direction, street_type, ward::int, community from all_sold_lots) UNION ALL (select cartodb_id, the_geom, the_geom_webmercator, pin, pin_nbr, street_name, street_direction, street_type, ward::int, community from " + LargeLots.cartodb_table + " where pin_nbr in (" + pins_sold + "))";
      }
      else {
          soldSQL = 'select * from all_sold_lots where false';
      }
      if(checks.indexOf('current') >= 0){
          currentSQL = 'select * from ' + LargeLots.cartodb_table + LargeLots.mainWhere;
      }
      else {
          currentSQL = 'select * from ' + LargeLots.cartodb_table + ' where false';
      }
      if(checks.indexOf('applied') >= 0){
          appliedSQL = 'select * from ' + LargeLots.cartodb_table + ' where pin_nbr in (' + pins_under_review + ')';
      }
      else {
          appliedSQL = 'select * from ' + LargeLots.cartodb_table + ' where false';
      }

      LargeLots.soldLotsLayer.setSQL(soldSQL);
      LargeLots.lotsLayer.setSQL(currentSQL);
      LargeLots.appliedLotsLayer.setSQL(appliedSQL);
  },

  checkZone: function (ZONING_CLA, value) {
    if (ZONING_CLA.indexOf(value) != -1)
      return true;
    else
      return false;
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
          if (typeof data.features[0] != 'undefined') {
            LargeLots.createParcelShape(data);
          }
        }).error(function(e){console.log(e)});

      window.location.hash = 'browse';
  },

  createParcelShape: function(data){
    var shape = data.features[0];
    LargeLots.lastClickedLayer = L.geoJson(shape);
    LargeLots.lastClickedLayer.addTo(LargeLots.map);
    LargeLots.lastClickedLayer.setStyle({fillColor:'#f7fcb9', weight: 2, fillOpacity: 1, color: '#000'});
    LargeLots.map.setView(LargeLots.lastClickedLayer.getBounds().getCenter(), 17);
    LargeLots.selectParcel(shape.properties);
  },

  selectParcel: function (props){
      info = LargeLots.createParcelInfo(props);

      $.address.parameter('pin', props.pin_nbr)
      $('#lot-info').html(info);

      $("#lot_apply").on("click", function(){
        if ($("#id_lot_1_pin").val() == "") {
          LargeLots.autopopulatePINAddress("1", this);
        }
        else if ($("#id_lot_1_pin").val() != $(this).data('pin')){
          LargeLots.autopopulatePINAddress("2", this);
        }

        $(this).html("<i class='fa fa-check'></i> Selected");
        $("#selected_lots").ScrollTo({offsetTop: "70px", 'axis':'y'});
      });
  },

  autopopulatePINAddress: function (lotNumber, buttonClicked) {
    $("#id_lot_" + lotNumber + "_address").val($(buttonClicked).data('address'));
    $("#id_lot_" + lotNumber + "_pin").val($(buttonClicked).data('pin'));
    if (!$(".group_id_lot_" + lotNumber).hasClass('has-error')) {
      $(".group_id_lot_" + lotNumber).addClass('has-success');
    }
  },

  createParcelInfo: function(props) {
      var address = LargeLots.formatAddress(props);
      var pin_formatted = LargeLots.formatPin(props.pin_nbr);
      var info = "<div class='row'><div class='col-xs-6 col-md-12'>\
        <table class='table table-bordered table-condensed'><tbody>\
          <tr><td>Address</td><td>" + address + "</td></tr>\
          <tr><td>PIN</td><td>" + pin_formatted + " (<a target='_blank' href='http://www.cookcountypropertyinfo.com/cookviewerpinresults.aspx?pin=" + props.pin_nbr + "'>info</a>)</td></tr>";
      if (props.zone_class){
          info += "<tr><td>Zoned</td><td> Residential (<a href='http://secondcityzoning.org/zone/" + props.zone_class + "' target='_blank'>" + props.zone_class + "</a>)</td></tr>";
      }
      if (props.square_feet){
          info += "<tr><td>Sq ft</td><td>" + LargeLots.addCommas(Math.floor(props.square_feet)) + "</td></tr>";

      }
      info += "<tr><td colspan='2'><button type='button' id='lot_apply' data-pin='" + pin_formatted + "' data-address='" + address + "' href='#' class='btn btn-success'>Select this lot</button></td></tr>"
      info += "</tbody></table></div><div class='col-xs-6 col-md-12'>\
      <img class='img-responsive img-thumbnail' src='https://pic.datamade.us/" + props.pin_nbr + ".jpg' /></div></div>";

      return info
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
          sql.execute("select cartodb_id, the_geom FROM {{boundaries}} AND ST_Intersects( the_geom, ST_SetSRID(ST_POINT({{lng}}, {{lat}}) , 4326))", {LargeLots:overlayName, lng:currentPinpoint[1], lat:currentPinpoint[0]})
          .done(function(data){
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
    var pin_str  = String(pin);
    return pin_str.replace(/(\d{2})(\d{2})(\d{3})(\d{3})(\d{4})/, '$1-$2-$3-$4-$5');
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
