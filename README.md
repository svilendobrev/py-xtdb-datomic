# try xtdb / datomic - temporal immutable dbs

These are similar temporal immutable dbs, in clojure + datalog. 
Providing something like automatic event-sourcing + cqrs , on somewhat lower-level, and using external storage-layers underneath

github.com/alexpetrov/datomic-xtdb-facts
vvvvalvalval.github.io/posts/2018-11-12-datomic-event-sourcing-without-the-hassle.html

status so far: 
 + representing edn-format/datalog in py - ok+tests
 + http-rest api wrapper-drivers - ok+tests
 ~ tests exist, not very ordered
 - all else is still in flux.. - schema, objmapper, unitofwork, etc
 + xtdb multinode , dockers
 	+ kafka, with kraft or zookeeper
	+ postgresql
	+ kafka+postgresql
	- partial-order in kafka ?
 - datomic multinode - not yet

