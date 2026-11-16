import {cpSync,mkdirSync,symlinkSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
mkdirSync('/work/project',{recursive:true});
cpSync('/input','/work/project',{recursive:true});
symlinkSync('/opt/engine/node_modules','/work/project/node_modules','dir');
execFileSync(process.execPath,['/opt/engine/render.mjs','/work/project',process.argv[2],'/output'],{stdio:'inherit'});
