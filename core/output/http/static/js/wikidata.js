function WikiDataItem ( init_wd , init_raw ) {

	// Variables
	this.wd = init_wd ;
	this.raw = init_raw ;
	this.placeholder = init_raw === undefined ;

	// Constructor

	// Methods
	this.isPlaceholder = function () { return this.placeholder ; }
	this.isItem = function () { return (this.raw||{ns:-1}).ns == 0 ; }
	this.isProperty = function () { return (this.raw||{ns:-1}).ns == 120 ; }
	this.getID = function () { return (this.raw||{}).id ; }

	this.getURL = function () {
		if ( typeof(this.raw) == 'undefined' ) return '' ;
		var ret = "//www.wikidata.org/wiki/" ;
		ret += this.raw.title ;
		return ret ;
	}

	this.getPropertyList = function () {
		var self = this ;
		var ret = [] ;
		$.each ( (self.raw.claims||{}) , function ( p , dummy ) {
			ret.push ( p ) ;
		} ) ;
		return ret ;
	}

	this.getLink = function ( o ) {
		var self = this ;
		if ( undefined === o ) o = {} ;
		var h = "<a " ;
		$.each ( ['target','class'] , function ( dummy , v ) {
			if ( undefined !== o[v] ) h += v + "='" + o[v] + "' " ;
		} ) ;
		if ( o.add_q ) h += "q='" + self.raw.title + "' " ;
		if ( undefined !== o.desc ) h += "title='" + self.getDesc() + "' " ;
		else h += "title='" + self.raw.title + "' " ;
		var url = self.getURL() ;
		h += "href='" + url + "'>" ;
		if ( o.title !== undefined ) h += o.title ;
		else if ( o.ucfirst ) h += ucFirst ( self.getLabel() ) ;
		else h += self.getLabel() ;
		h += "</a>" ;
		return h ;
	}

	this.getAliases = function ( include_labels ) {
		var self = this ;
		var ret = [] ;
		var aliases = {} ;
		$.each ( (self.raw.aliases||{}) , function ( lang , v1 ) {
			$.each ( v1 , function ( k2 , v2 ) {
				aliases[v2.value] = 1 ;
			} ) ;
		} ) ;
		if ( include_labels ) {
			$.each ( (self.raw.labels||{}) , function ( lang , v1 ) {
				aliases[v1.value] = 1 ;
			} ) ;
		}
		$.each ( aliases , function ( k , v ) { ret.push ( k ) } ) ;
		return ret ;
	}

	this.getAliasesForLanguage = function ( lang , include_labels ) {
		var self = this ;
		var ret = [] ;
		var aliases = {} ;
		var v1 = ((self.raw.aliases||{})[lang]||{}) ;
		$.each ( v1 , function ( k2 , v2 ) {
			aliases[v2.value] = 1 ;
		} ) ;
		if ( include_labels ) {
			var v1 = (self.raw.labels||{})[lang] ;
			if ( typeof v1 != 'undefined' ) aliases[v1.value] = 1 ;
		}
		$.each ( aliases , function ( k , v ) { ret.push ( k ) } ) ;
		return ret ;
	}

	this.getStringsForProperty = function ( p ) {
		return this.getMultimediaFilesForProperty ( p ) ;
	}

	this.getMultimediaFilesForProperty = function ( p ) {
		var self = this ;
		var ret = [] ;
		var claims = self.getClaimsForProperty ( p ) ;
		$.each ( claims , function ( dummy , c ) {
			var s = self.getClaimTargetString ( c ) ;
			if ( undefined === s ) return ;
			ret.push ( s ) ;
		} ) ;
		return ret ;
	}

	this.getClaimsForProperty = function ( p ) {
		p = this.wd.convertToStringArray ( p , 'P' ) [0] ;
		if ( undefined === this.raw || undefined === this.raw.claims ) return [] ;
		return this.raw.claims[this.wd.getUnifiedID(p)]||[] ;
	}

	this.hasClaims = function ( p ) {
		var claims = this.getClaimsForProperty ( p ) ;
		return claims.length > 0 ;
	}

	this.getClaimLabelsForProperty = function ( p ) {
		var self = this ;
		var ret = [] ;
		var claims = self.getClaimsForProperty ( p ) ;
		$.each ( claims , function ( dummy , c ) {
			var q = self.getClaimTargetItemID ( c ) ;
			if ( q === undefined ) return ;
			if ( undefined === self.wd.items[q] ) return ;
			ret.push ( self.wd.items[q].getLabel() ) ;
		} ) ;
		return ret ;
	}

	this.getClaimItemsForProperty = function ( p , return_all ) {
		var self = this ;
		var ret = [] ;
		var claims = self.getClaimsForProperty ( p ) ;
		$.each ( claims , function ( dummy , c ) {
			var q = self.getClaimTargetItemID ( c ) ;
			if ( q === undefined ) return ;
			if ( undefined === self.wd.items[q] && !return_all ) return ;
			ret.push ( q ) ;
		} ) ;
		return ret ;
	}

	this.getSnakObject = function ( s ) {
		var o = {} ;
		if ( undefined === s ) return o ;

		if ( undefined !== s.datavalue ) {
			if ( s.datavalue.type == 'wikibase-entityid' ) {
				o.type = 'item' ;
				o.q = 'Q' + s.datavalue.value['numeric-id'] ;
				o.key = o.q ;
			} else if ( s.datavalue.type == 'string' ) {
				o.type = 'string' ;
				o.s = s.datavalue.value ;
				o.key = o.s ;
			} else if ( s.datavalue.type == 'time' ) {
				o.type = 'time' ;
				$.extend ( true , o , s.datavalue.value ) ;
				o.key = o.time ; // TODO FIXME
			} else if ( s.datavalue.type == 'quantity' ) {
				o.type = 'quantity' ;
				$.extend ( true , o , s.datavalue.value ) ;
				o.key = o.amount ; // TODO FIXME
			}
		}
		return o ;
	}

	this.getClaimObjectsForProperty = function ( p ) {
		var self = this ;
		var ret = [] ;
		var claims = self.getClaimsForProperty ( p ) ;
		$.each ( claims , function ( dummy , c ) {
			var o = self.getSnakObject ( c.mainsnak ) ;
			if ( o.type === undefined ) return ;
			o.rank = c.rank ;
			o.qualifiers = {} ;
			$.each ( (c.qualifiers||[]) , function ( qp , qv ) {
				o.qualifiers[qp] = [] ;
				$.each ( qv , function ( k , v ) {
					o.qualifiers[qp].push ( self.getSnakObject ( v ) ) ;
				} ) ;
			} ) ;
			ret.push ( o ) ;
		} ) ;
		return ret ;
	}

	this.getDesc = function ( language ) {
		var self = this ;
		var desc = '' ;
		if ( undefined === language ) {
			$.each ( self.wd.main_languages , function ( dummy , lang ) {
				var l = self.getDesc ( lang ) ;
				if ( l == desc ) return ;
				desc = l ;
				return false ;
			} ) ;
		} else {
			if ( self.raw !== undefined && self.raw.descriptions !== undefined &&
				self.raw.descriptions[language] !== undefined && self.raw.descriptions[language].value !== undefined )
					desc = self.raw.descriptions[language].value ;
		}
		return desc ;
	}

	this.getLabelDefaultLanguage = function () {
		var self = this ;
		var default_label = self.getID() ; // Fallback
		var ret = '' ;
		$.each ( self.wd.main_languages , function ( dummy , lang ) {
			var l = self.getLabel ( lang ) ;
			if ( l == default_label ) return ;
			ret = lang ;
			return false ;
		} ) ;
		return ret ;
	}

	this.getLabel = function ( language ) {
		var self = this ;
		var label = self.getID() ; // Fallback
		if ( undefined === language ) {
			$.each ( self.wd.main_languages , function ( dummy , lang ) {
				var l = self.getLabel ( lang ) ;
				if ( l == label ) return ;
				label = l ;
				return false ;
			} ) ;
		} else {
			if ( self.raw !== undefined && self.raw.labels !== undefined &&
				self.raw.labels[language] !== undefined && self.raw.labels[language].value !== undefined )
					label = self.raw.labels[language].value ;
		}
		return label ;
	}

	this.getWikiLinks = function () {
		if ( typeof(this.raw) == 'undefined' ) return {} ;
		return (this.raw.sitelinks||{}) ;
	}

	this.getClaimRank = function ( claim ) {
		if ( claim === undefined ) return undefined ;
		return claim.rank || 'normal' ; // default
/*		if ( claim.rank === undefined ) return undefined ;
		if ( claim.rank == 'normal' ) return 0 ;
		if ( claim.rank == 'deptecated' ) return -1 ;
		if ( claim.rank == 'preferred' ) return 1 ;
		return undefined ;*/
	}

	this.getClaimTargetItemID = function ( claim ) {
		if ( claim === undefined ) return undefined ;
		if ( claim.mainsnak === undefined ) return undefined ;
		if ( claim.mainsnak.datavalue === undefined ) return undefined ;
		if ( claim.mainsnak.datavalue.value === undefined ) return undefined ;
		if ( claim.mainsnak.datavalue.value['entity-type'] != 'item' ) return undefined ;
		if ( claim.mainsnak.datavalue.value['numeric-id'] === undefined ) return undefined ;
		return 'Q'+claim.mainsnak.datavalue.value['numeric-id'] ;
	}

	this.getClaimTargetString = function ( claim ) {
		if ( claim === undefined ) return undefined ;
		if ( claim.mainsnak === undefined ) return undefined ;
		if ( claim.mainsnak.datavalue === undefined ) return undefined ;
		if ( claim.mainsnak.datavalue.type === undefined ) return undefined ;
		if ( claim.mainsnak.datavalue.type != 'string' ) return undefined ;
		return claim.mainsnak.datavalue.value ;
	}

	this.getClaimDate = function ( claim ) {
		if ( claim === undefined ) return undefined ;
		if ( claim.mainsnak === undefined ) return undefined ;
		if ( claim.mainsnak.datavalue === undefined ) return undefined ;
		if ( claim.mainsnak.datavalue.type === undefined ) return undefined ;
		if ( claim.mainsnak.datavalue.type != 'time' ) return undefined ;
		return claim.mainsnak.datavalue.value ;
	}

	this.hasClaimItemLink = function ( p , q ) {
		var self = this ;
		var ret = false ;
		q = this.wd.convertToStringArray ( q , 'Q' ) [0] ;
		var claims = self.getClaimsForProperty ( p ) ;
		$.each ( claims , function ( dummy , c ) {
			var id = self.getClaimTargetItemID ( c ) ;
			if ( id === undefined || id != q ) return ;
			ret = true ;
			return false ;
		} ) ;
		return ret ;
	}

	this.followChain = function ( o ) {
		var self = this ;
		var id = self.getID() ;
		if ( undefined === self.wd ) {
			console.log ( "ERROR : followChain for " + id + " has no wd object set!" ) ;
			return ;
		}
		if ( o.hadthat === undefined ) {
			o.hadthat = {} ;
			o.longest = [] ;
			o.current = [] ;
			o.props = self.wd.convertToStringArray ( o.props , 'P' ) ;
		}
		if ( undefined !== o.hadthat[id] ) return ;
		o.hadthat[id] = 1 ;
		o.current.push ( id ) ;
		if ( o.current.length > o.longest.length ) o.longest = $.extend(true, [], o.current);

		var tried_item = {} ;
		$.each ( o.props , function ( dummy , p ) {
			var items = self.getClaimItemsForProperty ( p ) ;
			$.each ( items , function ( dummy , q ) {
				if ( -1 != $.inArray ( q , o.current ) ) return ; // Already on that
				if ( tried_item[q] ) return ; // Only once my dear
				tried_item[q] = true ;
				self.wd.getItem(q).followChain(o) ;
			} ) ;
/*			var claims = self.getClaimsForProperty ( p ) ;
			$.each ( claims , function ( dummy , c ) {
				var q = self.getClaimTargetItemID ( c ) ;
				if ( q === undefined ) return ;
				var i = self.wd.getItem ( q ) ;
				if ( i !== undefined ) i.followChain ( o ) ;
			} ) ;*/
		} ) ;

		delete o.hadthat[this.getID()] ;
		o.current.pop() ;
		if ( o.current.length == 0 ) return o.longest ;
	}

}

function WikiData () {

	// Variables
	this.api = '//www.wikidata.org/w/api.php?callback=?' ;
	this.max_get_entities = 50 ;
	this.max_get_entities_smaller = 25 ;
	this.language = 'en' ; // Default
	this.main_languages = [ 'en' , 'de' , 'fr' , 'nl' , 'es' , 'it' , 'pl' , 'pt' , 'ja' , 'ru' , 'hu' , 'sv' , 'fi' ] ;
	this.items = {} ;

	// Constructor
//	this.clear() ;

	// Methods
	this.clear = function () {
		this.items = {} ;
	}

	this.countItemsLoaded = function () {
		var self = this ;
		var ret = 0 ;
		$.each ( self.items , function ( k , v ) { if ( !v.isPlaceholder() && v.isItem() ) ret++ } ) ;
		return ret ;
	}

	this.getUnifiedID = function ( name , type ) {
		var ret = String(name).replace ( /\s/g , '' ).toUpperCase() ;
		if ( /^\d+$/.test(ret) && undefined !== type ) ret = type.toUpperCase() + ret ;
		return ret ;
	}

	this.getItem = function ( q ) {
		return this.items[this.getUnifiedID(q)] ;
	}

	this.convertToStringArray = function ( o , type ) {
		var self = this ;
		var ret = [] ;
		if ( o === undefined ) return ret ;
		if ( o instanceof Array || o instanceof Object ) {
			$.each ( o , function ( k , v ) {
				ret.push ( self.getUnifiedID(v,type) ) ;
			} ) ;
		} else {
			ret = [ self.getUnifiedID(o,type) ] ;
		}
		return ret ;
	}

	this.getLinksForItems = function ( ql , o , fallback ) {
		var self = this ;
		if ( undefined === fallback ) fallback = '' ;
		var a = [] ;
		$.each ( self.convertToStringArray ( ql , 'Q' ) , function ( dummy , q ) {
			if ( undefined === self.items[q] ) return ;
			a.push ( self.items[q].getLink ( o ) ) ;
		} ) ;
		if ( a.length == 0 ) return fallback ;
		return a.join ( '; ' ) ;
	}


	this.getItemBatch = function ( item_list , callback , props ) {
		var self = this ;
		if ( props === undefined ) props = 'info|aliases|labels|descriptions|claims|sitelinks|datatype' ;
		var ids = [ [] ] ;
		self.loaded_count = 0 ;
		self.loading_count = 0 ;
		max_per_batch = item_list.length > 100 ? self.max_get_entities : self.max_get_entities_smaller ; // Smaller batch size for small list
		$.each ( item_list , function ( dummy , q ) {
			if ( typeof q == 'number' ) q = 'Q' + q ;
			if ( self.items[q] !== undefined ) return ; // Have that one
			if ( -1 != $.inArray ( q , ids ) ) return ; // Already planning to load that one
			if ( ids[ids.length-1].length >= max_per_batch ) ids.push ( [] ) ;
			ids[ids.length-1].push ( q ) ;
			self.loading_count++ ;
		} ) ;

		if ( ids[0].length == 0 ) { // My work here is done
			callback ( ids ) ;
			return ;
		}

		if ( ids.length > 1 ) {
			var last = ids.length-1 ;
			while ( ids[last].length+last <= max_per_batch && ids[last].length+last <= ids[0].length ) {
				for ( var i = 0 ; i < last ; i++ ) {
					ids[last].push ( ids[i].pop() ) ;
				}
			}
		}

		var running = ids.length ;
		$.each ( ids , function ( dummy , id_list ) {
			$.getJSON ( self.api , {
				action : 'wbgetentities' ,
				ids : id_list.join('|') ,
				props : props ,
				format : 'json'
			} , function ( data ) {

				$.each ( (data.entities||[]) , function ( k , v ) {
					var q = self.getUnifiedID ( k ) ;
					self.items[q] = new WikiDataItem ( self , data.entities[q] ) ;
					self.loaded_count++ ;
				} ) ;

				if ( undefined !== self.loading_status_callback ) self.loading_status_callback ( self.loaded_count , self.loading_count ) ;

				running-- ;
				if ( running == 0 ) callback ( ids ) ;
			} ) ;
		} ) ;

	}


	/**
	Loads a list of items, follows property list if given
	- item_list : array of strings/integers with item (q/p) IDs
	- params: Object
	-- follow : array (property values to follow)
	-- preload : array (property values to download items for, but not follow)
	-- preload_all_for_root : download all linked items for properties in the root element
	-- status : function ( params )
	-- loaded : function ( q , params )
	-- finished : function ( params )
	- max_depth : integer (0=no follow;1=follow 1 depth etc.) or undefined for unlimited
	*/
	this.loadItems = function ( item_list , params , max_depth ) {
		var self = this ;

		if ( undefined !== max_depth ) {
			if ( max_depth < 0 ) return ;
			max_depth-- ;
		}

		// Initialize parameters, and seeds on initial run
		var first = false ;
		var download_all_linked_items = false ;
		var ql = [] ;
		if ( undefined === params ) params = {} ;
		if ( undefined === params.running ) {
			first = true ;
			if ( params.preload_all_for_root ) download_all_linked_items = true ;
			params.running = 0 ;
			params.post_load_items = [] ;
			params.preload = self.convertToStringArray ( params.preload , 'P' ) ;
			params.follow = self.convertToStringArray ( params.follow , 'P' ) ;
			ql = self.convertToStringArray ( item_list , 'Q' ) ; // 'Q' being the default, in case only integers get passed
			if ( undefined !== params.status ) params.status ( params ) ;
		} else {
			ql = item_list ;
		}

		// Run through list, and self-call where necessary
		var started = false ;
		while ( ql.length > 0 ) {
			var ids = [] ;
			while ( ids.length < self.max_get_entities && ql.length > 0 ) {
				var q = ql.shift() ;
				if ( self.items[q] !== undefined && !self.items[q].placeholder ) continue ; // Done that
				if ( self.items[q] === undefined ) self.items[q] = new WikiDataItem ( self ) ;
				ids.push ( q ) ;
			}
			if ( ids.length == 0 ) continue ;
			params.running++ ;
			started = true ;
			if ( undefined !== params.status ) params.status ( params ) ;
			var call_params = {
				action : 'wbgetentities' ,
				ids : ids.join('|') ,
//				languages : self.main_languages.join('|') ,
				props : 'info|aliases|labels|descriptions|claims|sitelinks' ,
				format : 'json'
			} ;
			if ( !first && params.languages !== undefined ) call_params.languages = params.languages ;
			$.getJSON ( self.api , call_params , function ( data ) {
				var nql = [] ;
				$.each ( (data.entities||[]) , function ( k , v ) {
					var q = self.getUnifiedID ( k ) ;
					self.items[q] = new WikiDataItem ( self , data.entities[q] ) ;
					if ( undefined !== params.loaded ) params.loaded ( q , params ) ;

					// Follow properties
					var si = self.items[q] ;
					var i = si.raw ;
					$.each ( (i.claims||{}) , function ( k2 , v2 ) {
						if ( -1 == $.inArray ( k2 , params.post_load_items ) ) params.post_load_items.push ( k2 ) ;
					} ) ;

					// Follow properties
					$.each ( params.follow , function ( dummy , p ) {
						$.each ( si.getClaimsForProperty ( p ) , function ( dummy2 , claim ) {
							var q2 = si.getClaimTargetItemID ( claim ) ;
							if ( undefined === q2 ) return ;
							if ( undefined !== self.items[q2] ) return ; // Had that
							if ( -1 != $.inArray ( q2 , nql ) ) return ; // Already on list
							nql.push ( q2 ) ;
						} )
					} ) ;

					// Add qualifiers
					$.each ( (i.claims||{}) , function ( k2 , v2 ) {
						$.each ( v2 , function ( k2a , v2a ) {
							$.each ( (v2a.qualifiers||[]) , function ( k3 , v3 ) {
								if ( -1 == $.inArray ( k3 , params.post_load_items ) ) params.post_load_items.push ( k3 ) ;
								$.each ( v3 , function ( k4 , v4 ) {
									if ( undefined === v4.datavalue ) return ;
									if ( undefined === v4.datavalue.value ) return ;
									if ( undefined === v4.datavalue.value['numeric-id'] ) return ;
									var qualq = 'Q'+v4.datavalue.value['numeric-id'] ;
									if ( -1 == $.inArray ( qualq , params.post_load_items ) ) params.post_load_items.push ( qualq ) ;
								} ) ;
							} ) ;
						} ) ;
					} ) ;

					// Add pre-load property targets to post-load list
					var pre ;
					if ( download_all_linked_items ) {
						pre = self.items[q].getPropertyList() ;
					} else pre = params.preload ;
					$.each ( pre , function ( dummy , p ) {
						$.each ( si.getClaimsForProperty ( p ) , function ( dummy2 , claim ) {
							var q2 = si.getClaimTargetItemID ( claim ) ;
							if ( undefined === q2 ) return ;
							if ( undefined !== self.items[q2] ) return ; // Had that
							if ( -1 != $.inArray ( q2 , params.post_load_items ) ) return ; // Already on list
							params.post_load_items.push ( q2 ) ;
						} )
					} ) ;

				} ) ;
				if ( nql.length > 0 ) {
					self.loadItems ( nql , params , max_depth ) ;
				}
				params.running-- ;
				if ( undefined !== params.status ) params.status ( params ) ;

				if ( params.running == 0 ) { // All loaded

					if ( params.post_load_items.length > 0 ) {
						self.loadItems ( params.post_load_items , {
							finished : function () {
								if ( undefined !== params.finished ) params.finished ( params ) ;
							}
						} , 0 ) ;
					} else {
						if ( undefined !== params.finished ) params.finished ( params ) ;
					}
				}
			} ) ;
		}

		if ( first && !started ) {
			if ( undefined !== params.finished ) params.finished ( params ) ;
		}
	}

}
