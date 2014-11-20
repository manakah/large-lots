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
      LargeLots.boundingBox = init_params.boundingBox;
      LargeLots.tableName = init_params.tableName;
      LargeLots.overlayName = init_params.overlayName;
      LargeLots.mainWhere = init_params.mainWhere;
      if (!LargeLots.map) {
        LargeLots.map = L.map('map', {
          center: LargeLots.map_centroid,
          zoom: LargeLots.defaultZoom,
          scrollWheelZoom: false
        });
      }
      // render a map!
      L.Icon.Default.imagePath = '/images/'

      L.tileLayer('https://{s}.tiles.mapbox.com/v3/datamade.hn83a654/{z}/{x}/{y}.png', {
          attribution: '<a href="http://www.mapbox.com/about/maps/" target="_blank">Terms &amp; Feedback</a>'
      }).addTo(LargeLots.map);

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
          info += "<p>PIN: " + props.pin14 + "<br />";
          info += "Zoned: " + props.zoning_classification + "<br />";
          info += "Sq Ft: " + props.sq_ft + "<br />";
          if (props.status == 1){
              info += "Status: <strong>Application received</strong></p>"
          } else {
              info += "Status: <strong>Available</strong></p>"
          }
          this._div.innerHTML  = info;
        }
      };

      LargeLots.info.clear = function(){
          this._div.innerHTML = '';
      }

      LargeLots.info.addTo(LargeLots.map);
      // We'll need to add a status column
      var fields = "pin14,zoning_classification,ward,street_name,street_dir,street_number,street_type,city_owned,residential"
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
      cartodb.createLayer(LargeLots.map, layerOpts)
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
      var sql = 'select * from lots_with_status where ';
      var clauses = []
      if(checks.indexOf('applied') >= 0){
          clauses.push('status = 2')
      }
      if(checks.indexOf('available') >= 0){
          clauses.push('status = 0')
      }
      if(clauses.length > 0){
          clauses = clauses.join(' or ');
          sql += clauses;
      } else {
          sql = 'select * from lots_with_status where status not in (0,1,2)'
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
    return prop.street_number + " " + prop.dir + " " + prop.street_name + " " + prop.type;
  },

  getOneParcel: function(pin14){
      if (LargeLots.lastClickedLayer){
        LargeLots.map.removeLayer(LargeLots.lastClickedLayer);
      }
      var sql = new cartodb.SQL({user: 'datamade', format: 'geojson'});
      sql.execute('select * from lots_with_status where pin14 = {{pin14}}', {pin14:pin14})
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
      var info = "<p>Selected lot: </p><img class='img-responsive img-thumbnail' src='http://cookviewer1.cookcountyil.gov/Jsviewer/image_viewer/requestImg.aspx?" + props.pin14 + "=' />\
        <table class='table table-bordered table-condensed'><tbody>\
          <tr><td>Address</td><td>" + address + "</td></tr>\
          <tr><td>PIN</td><td>" + props.pin14 + "</td></tr>\
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
    var searchRadius = $("#search_address").val();
    if (searchRadius != '') {

      var raw_address = $("#search_address").val().toLowerCase();
      raw_address = raw_address.replace(" n ", " north ");
      raw_address = raw_address.replace(" s ", " south ");
      raw_address = raw_address.replace(" e ", " east ");
      raw_address = raw_address.replace(" w ", " west ");

      if(LargeLots.locationScope && LargeLots.locationScope.length){
        var checkaddress = raw_address.toLowerCase();
        var checkcity = LargeLots.locationScope.split(",")[0].toLowerCase();
        if(checkaddress.indexOf(checkcity) == -1){
          raw_address += ", " + LargeLots.locationScope;
        }
      }

      $.address.parameter('address', encodeURIComponent(raw_address));

      var s = document.createElement("script");
      s.type = "text/javascript";
      s.src = "http://nominatim.openstreetmap.org/search/" + encodeURIComponent(raw_address) + "?format=json&bounded=1&viewbox=" + LargeLots.boundingBox['left'] + "," + LargeLots.boundingBox['top'] + "," + LargeLots.boundingBox['right'] + "," + LargeLots.boundingBox['bottom'] + "&json_callback=LargeLots.returnAddress";
      document.body.appendChild(s);
      //&bounded=1&viewbox=" + LargeLots.boundingBox['left'] + "," + LargeLots.boundingBox['top'] + "," + LargeLots.boundingBox['right'] + "," + LargeLots.boundingBox['bottom'] + "
    }
  },

  returnAddress: function (response){

    if(!response.length){
      $('#modalGeocode').modal('show');
      return;
    }

    var first = response[0];

    LargeLots.map.setView([first.lat, first.lon], 17);

    if (LargeLots.marker)
      LargeLots.map.removeLayer( LargeLots.marker );

    var defaultIcon = L.icon({
        iconUrl: 'images/marker-icon.png',
        shadowUrl: 'images/marker-shadow.png',
        shadowAnchor: [0, 0]
      });
    LargeLots.marker = L.marker([first.lat, first.lon]).addTo(LargeLots.map);
  },

  //converts a slug or query string in to readable text
  convertToPlainString: function (text) {
    if (text == undefined) return '';
    return decodeURIComponent(text);
  }

}
