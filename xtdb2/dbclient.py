from base.rpc_edn_json_http import BaseClient, hacks, log #dict_without_None
hacks.edn_accept_naive_datetimes()  #tx-as-json
#XXX TODO does it need further hacks ? .. see dbclient.RESULT_EDN
import edn_format
Keyword = edn_format.Keyword
Symbol  = edn_format.Symbol
edn_dumps = edn_format.dumps
import pprint

class List( tuple):
    def __new__( me, *a):
        return super().__new__( me, a)
class XTQLop( List):
    pass

from transit.transit_types import TaggedValue

def transit_dumps( x):
    #print( 333333, x)
    if 0:   #for original transit-python, not needed for transit-python2
        import collections.abc
        for c in 'MutableMapping Mapping Hashable'.split():
            setattr( collections, c, getattr( collections.abc, c))
    from transit.writer import Writer
    from transit.write_handlers import KeywordHandler, SymbolHandler, MapHandler, SetHandler, TaggedMap, ArrayHandler
    from transit.transit_types import Keyword as tj_Keyword
    from io import StringIO
    buf = StringIO()
    w = Writer( buf, 'json' )
    class KeywordHandler2( KeywordHandler):
        @staticmethod
        def rep(k): return k.name
        string_rep = rep
    class MapHandler2( MapHandler):
        @staticmethod
        def rep(m):
            return dict( (tj_Keyword( k) if not isinstance(k, (Keyword,tj_Keyword)) else k,v)
                    for k,v in m.items())
    w.register( Keyword, KeywordHandler2 ) #w.marshaler.handlers[
    w.register( Symbol,  SymbolHandler ) #w.marshaler.handlers[
    w.register( dict,  MapHandler2 ) #w.marshaler.handlers[

    class ListHandler:
        @staticmethod
        def tag(_): return 'list'
        @staticmethod
        def rep(s): return list(s)
    if 1:
        #w.register( List,  ListHandler)     #tuple==list==array/vector
        w.register( tuple, ListHandler)     #tuple -> xtdb/list i.e. sequence ; list -> vector

    class XTQLopHandler:
        @staticmethod
        def tag(s): return 'xtdb.tx/'+s[0]
        @staticmethod
        def rep(s): return s[1]
    w.register( XTQLop, XTQLopHandler)

    w.write( x )
    value = buf.getvalue()
    print( '\n  '.join( ['tj-dump',
        'in: '+ str(x),
        'out: '+ value,
        #'edn:'+ edn_dumps( x),
        'und:'+ str( transit_loads( value)),
        ]))
    return value

from transit import transit_types

def transit_loads( x, multi =False):
    from transit.reader import Reader
    from io import StringIO
    #x = x.decode( 'utf8')      #hope it's utf8 XXX
    if multi:
        x = '[' + x.replace( '] [', '],[') + ']'    #jsonize a space-delimited stream of jsons
    buf = StringIO( x)
    #from transit.reader import JsonUnmarshaler
    #r = JsonUnmarshaler().load( buf)
    r = Reader( protocol= 'json')
    #from transit.transit_types import Keyword as tj_Keyword
    from transit import transit_types
    from transit.read_handlers import KeywordHandler, SymbolHandler, CmapHandler, pairs, DateHandler, ListHandler
    if not getattr( KeywordHandler, '_dbclixed', 0):
        KeywordHandler._dbclixed = 1
        KeywordHandler.from_rep = Keyword    #staticmethod
        #SymbolHandler.from_rep = staticmethod( Symbol )
        #CmapHandler.from_rep = staticmethod( lambda cmap: dict( pairs( cmap))) not needed if below frozendict
        transit_types.frozendict = edn_format.ImmutableDict #dict   auto keyword2str, kebab2camel, etc
        transit_types.TaggedValue.__repr__ = lambda me: me.tag+'::::\n   '+pprint.pformat( me.rep).replace('\n','\n   ')
        r.register( 'time/instant', DateHandler)
        class txkey_dict( edn_format.ImmutableDict ): pass  #dict
        class txkey_handler: from_rep = txkey_dict
        r.register( 'xtdb/tx-key', txkey_handler)

    rr = r.read( buf)
    #rr = list( r.readeach( buf))   #hangs forever
    #print( 5555, rr)
    #if isinstance( rr, dict):
    #    for k,v in  list( rr.items()): print( k,'::', v, type(v))
    return rr
    #TODO
    # dict key/keywords -> text -> kebab2camel/ edn_response_Keyword_into_str above

if 0:
    import functools
    def nonv2( f ):
        @functools.wraps( f)
        def wrapper( me, *a,**ka):
            assert not me.is_v2
            return f( me, *a,**ka)
        return wrapper

sym_pipeline = Symbol( '->')

class xtdb2_read( BaseClient):
    '''
    https://docs.xtdb.com/reference/main.html
    ./v2/openapi.yaml
    TODO: sql
    '''

    _app_transit_json = 'application/transit+json'
    _headers_content_tjson = { 'content-type': _app_transit_json }
    _headers_base = dict(
        _headers_content_tjson,
        #'accept' : BaseClient._app_json,   #text/plain text/html
        #**BaseClient._headers_content_json,
        accept= _app_transit_json,
        )
    _headers_json = dict(
        BaseClient._headers_content_json,
        accept= BaseClient._app_json,
        )

    if 0:
      def _response( me, r, tj_multi =False):
        result = super()._response( r)
        if isinstance( result, bytes):
            return transit_loads( result.decode( 'utf8'), multi= tj_multi)  #hope it is utf8 ?
        return result

    id_name = 'xt/id'       #use in objs/dicts i/o data , in json
    id_sql  = id_name.replace( '/', '$')
    id_kw   = Keyword( id_name)

    ##### rpc methods
    debug = 1
    def status( me): return me._get( 'status')
    def latest_completed_tx( me): return me.status()[ 'latestCompletedTx' ]
    def latest_submitted_tx( me): return me.status()[ 'latestSubmittedTx' ]
    def openapi_yaml( me): return me._get( 'openapi.yaml')

    def query( me, query, *in_args,
                    tz_default =None,
                    valid_time_all =False,
                    #basis = at_tx #as returned in submit_tx
                    #basis-timeout_s    ??
                    #as_json =False,
                    after_tx =None,
                            #TaggedValue( 'xtdb/tx-key', { 'tx-id': 612343,
                                        # 'system-time':
                                            #TaggedValue( 'time/instant',"2024-01-10T11:08:36.422964Z")
                                            #datetime.datetime( 2024, 1, 10, 11, 8, 36, 422964, tzinfo =datetime.UTC)
                    **ka):
        query = dict( query= query,)
        '''     {
                "query": xtdb/list( (from ..) ),
                "basis": null or { :at-tx: .. },
                "basis-timeout": null, ??
                "args": [ {} ], ??
                "default-all-valid-time?": true,
                "default-tz": null ??
                }
            https://docs.xtdb.com/reference/main/xtql/queries.html
            '''
        if in_args: query[ 'args'] = in_args
        if tz_default: query[ 'default-tz'] = tz_default
        if valid_time_all: query[ 'default-all-valid-time?'] = valid_time_all
        if after_tx: query[ 'after-tx'] = after_tx
        #..

        query = transit_dumps( query)

        assert not in_args  #TODO
        assert not ka       #TODO

        return me._post( 'query',
                data= query,
                ka_response= dict( tj_multi= True),     #XXX if not as_json
                #if as_json: headers= me._headers_json
                )

    def _content( me, r, tj_multi =False, **ka):
        contentype = r.headers.get( 'content-type', '')
        if me._app_transit_json in contentype:
            return transit_loads( r.text, multi= tj_multi)  #decode? utf-8? XXX
        return super()._content( r, **ka)

    def _post( me, *a,**ka):
        try:
            return super()._post( *a,**ka)
        except RuntimeError as e:
            r = e.response
            cooked = me._content( r)    #no multi here XXX
            if cooked:
                text = str( cooked)
                e.args = ( e.args[0] + '\n>>>> '+text.replace('\n','\n>>')+'\n', *e.args[1:] )
            raise

class xtdb2( xtdb2_read):
    def submit_tx( me, docs, tz_default =None, tx_time =None, valid_time_from_to =None, as_json =False):
        '''
        tx_time: system-time: overrides system-time for the transaction, mustn’t be earlier than any previous system-time.
        tz_default: default-tz: overrides the default time zone for the transaction
        '''
        #TODO inside-doc valid/end-time that may or may not be funcs
        #TODO SQL is unclear - texts or what
        if 0:
            import datetime
            valid_time_from_to = [ datetime.datetime( 2023, 2, 3, 4, 5 ), None ]
        valid_time_from_to = valid_time_from_to and [ me.may_time( x) for x in valid_time_from_to ]
        tx_time = me.may_time( tx_time)

        if isinstance( docs, dict): docs = [ docs ]
        assert isinstance( docs, (list,tuple)), docs
        for d in docs:
            assert isinstance( d, dict), d

        docs = [ me.make_tx_put( d, valid_time_from_to= valid_time_from_to, as_json= as_json)
                 if isinstance( d, dict)
                 else d
                for d in docs ]
        for d in docs:
            assert d[0] in me._transaction_types, d[0]

                 #XTQLop( op, dict...
        docs = [ TaggedValue( 'xtdb.tx/'+op, { 'table-name': tbl, 'doc': doc, **tt })
                    for op,tbl,doc,tt in docs ]    #xtql-jan24

        ops = { 'tx-ops': docs }     #XXX assume auto key->keyword
        if tx_time or tz_default:   #general for whole tx
            ops[ 'opts' ] = {
                'system-time': tx_time,     #XXX XTQL only?
                'default-tz':  tz_default,  #XXX XTQL only?
                #'default-all-valid-time?': bool # XXX ? SQL only??
                }
        data = transit_dumps( ops)
        return me._post( 'tx',
                data= data,
                #if as_json: headers= me._headers_json
                )

    write = save = tx = submit_tx

    _transaction_types = '''
        put delete erase
        insert-into assert-exists assert-not-exists
        call put-fn
        '''.split()    #call = v1.fn ; erase = v1.evict
        ##update-table delete-from erase-from

    _time_valid_from  = 'valid-from'
    _time_valid_to    = 'valid-to'
    @staticmethod
    def _kw_as_json( name, as_json):
        if as_json: return name
        return Keyword( 'xt/'+name)
    @classmethod
    def _use_valid_time( me, tx, valid_time_from_to =None, as_json =False):
        tt = {}
        if valid_time_from_to:
            time_valid_from, time_valid_to = valid_time_from_to
            if time_valid_from:
                tt[ me._time_valid_from ] = time_valid_from
            if time_valid_to:
                tt[ me._time_valid_to ] = time_valid_to
        return [ *tx, tt ]

        #r = [ sym_pipeline, tx ]
        #time_valid_from, time_valid_to = valid_time_from_to
        #if time_valid_from and time_valid_to:
        #    return r + [[ me._kw_as_json( me._time_valid_from_to, as_json), time_valid_from, time_valid_to ]]
        #if time_valid_from:
        #    return r + [[ me._kw_as_json( me._time_valid_from, as_json), time_valid_from ]]
        #if time_valid_to:
        #    return r + [[ me._kw_as_json( me._time_valid_to, as_json), time_valid_to ]]
        #return tx

    @staticmethod
    def _table_as_json( table, as_json):
        if as_json:
            assert isinstance( table, str), table
        else:
            if isinstance( table, str): table = Keyword( table)
            assert isinstance( table, Keyword), table
        return table

    @classmethod
    def make_tx_put( me, doc, *, table ='atablename', as_json =False, **ka):
        if as_json or 1:    #always, dicts are auto-keyworded later
            assert doc.get( me.id_name), doc    #for json
        else:
            assert doc.get( me.id_kw), doc      #for edn/transit
        table = me._table_as_json( table, as_json)
        tx = [ 'put', table, dict( doc) ]
        return me._use_valid_time( tx, as_json= as_json, **ka)
    @classmethod
    def make_tx_delete( me, eid, *, table ='atablename', **ka):
        table = me._table_as_json( table, as_json)
        tx = [ 'delete', table, eid ]
        return me._use_valid_time( tx, **ka)
    @classmethod
    def make_tx_erase( me, eid, *, table ='atablename'):
        table = me._table_as_json( table, as_json)
        return [ 'erase', table, eid ]

    @classmethod
    def make_tx_insert_into( me, query, table ='atablename', as_json =False):
        '''To specify a valid-time range, the query may return xt/valid-from and/or xt/valid-to columns. If not provided, these will default as per put'''
        table = me._table_as_json( table, as_json)
        return [ 'insert-into', table, query ]
    @staticmethod
    def make_tx_assert_exists( query):
        return [ 'assert-exists', query ]
    @staticmethod
    def make_tx_assert_notexists( query):
        return [ 'assert-not-exists', query ]

    #TODO : update-table delete-from erase-from

    #these are unclear
    @staticmethod
    def make_tx_func_decl( funcname, body):
        if isinstance( funcname, str): funcname = Keyword( funcname)
        assert isinstance( funcname, Keyword), funcname
        return [ 'put-fn', funcname, body ]
    @staticmethod
    def make_tx_func_use( funcname, *args):
        if isinstance( funcname, str): funcname = Keyword( funcname)
        assert isinstance( funcname, Keyword), funcname
        return [ 'call', funcname, *args ]

# vim:ts=4:sw=4:expandtab
