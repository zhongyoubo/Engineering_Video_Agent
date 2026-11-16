import {PGlite} from '@electric-sql/pglite';
import {PGLiteSocketServer} from '@electric-sql/pglite-socket';
const db=await PGlite.create();
const server=new PGLiteSocketServer({db,host:'127.0.0.1',port:55433});
await server.start();console.log('PGlite PostgreSQL protocol engine ready 55433');
process.on('SIGTERM',async()=>{await server.stop();await db.close();process.exit(0)});
