# Selfhost Excalidrawa

**example custom**

[https://blog.excalidraw.com/end-to-end-encryption/](https://blog.excalidraw.com/end-to-end-encryption/)

|  |   | Firebase |
| --- | --- | --- |
|  |  |  |
|  |  |  |
|  |  |  |

saveToHttpStorage //*saveCollabRoomToFirebase*

# Roadmap

- [ ]  Mute
- [ ]  MailServer
- [ ]  Login by mail
- [ ]  NextJs server
- [ ]  Not Found Page

# Bugs

- [ ]  Out room still records
- [ ]  

# Design

## Requriement

### Relation

**1- Workspace**:

- M -  Collections - M — M - Teams
    - M - Scenes
- M - Members:
    - M - Admin - 1 OWNER (DELETED or change role other) - (*Admins can add/remove workspace users, and manage subscription/billing. More granular permissions coming soon.*)
    - M - User (Members can add/remove collections, and access and edit scenes within ([Workspace Teams](https://app.excalidraw.com/o/3rzG1yGrEM/settings/teams) rules may apply).)

**Collection** - Team:

Assign If 1 collection not assign every one can join 

1 Mem 1 one workspace have 1 private collection default 

⇒ [Table]: Collection: isPrivate

### Worksapce

Many user:

- Admin
    - 1 ADMIN (Owner) - created
- 
- User

Many Teams

Many Collections

Many Sence 

### Create invite link

/workspace/3rzG1yGrEM/invite/link

```json
{ 
	maxUses: 2
	restrictedDomains: null
	role: "member"
	type: "link" 
}
```

```json
{
    "status": "pending",
    "type": "link",
    "created": "2024-07-20T04:27:07.851Z",
    "email": null,
    "resolvedAt": null,
    "redeemedBy": null,
    "role": "member",
    "maxUses": 2,
    "uses": 0,
    "restrictedDomains": null,
    "id": "5vo0QEBxw9f"
}
```

StorageBackend.ts

```tsx
import type {
  isSavedToFirebase,
  loadFilesFromFirebase,
  loadFromFirebase,
  saveFilesToFirebase,
  saveToFirebase,
} from "./firebase";

export interface IStorageBackend {
  isSaved: typeof isSavedToFirebase;
  saveToStorage: typeof saveToFirebase;
  loadFromStorage: typeof loadFromFirebase;
  saveFilesToStorage: typeof saveFilesToFirebase;
  loadFilesFromStorage: typeof loadFilesFromFirebase;
}

export interface StoredScene {
  sceneVersion: number;
  iv: Blob;
  ciphertext: Blob;
}

```

httpStorage.ts

```tsx
import type { Socket } from "socket.io-client";
import { MIME_TYPES } from "../../packages/excalidraw";
import { decompressData } from "../../packages/excalidraw/data/encode";
import type {
  ExcalidrawElement,
  FileId,
  OrderedExcalidrawElement,
} from "../../packages/excalidraw/element/types";
import type Portal from "../collab/Portal";
import { hashElementsVersion } from "./../../packages/excalidraw/element/index";
import type {
  AppState,
  BinaryFileData,
  BinaryFileMetadata,
  DataURL,
} from "./../../packages/excalidraw/types";
import { getSyncableElements, type SyncableExcalidrawElement } from ".";
import type { IStorageBackend } from "./StorageBackend";
import type { RemoteExcalidrawElement } from "../../packages/excalidraw/data/reconcile";
import { reconcileElements } from "../../packages/excalidraw/data/reconcile";
import storageApi from "../../packages/excalidraw/http/storage.api";

const HTTP_STORAGE_BACKEND_URL = import.meta.env.VITE_HTTP_STORAGE_BACKEND_URL;

class HttpStorageSceneVersionCache {
  private static cache = new WeakMap<Socket, number>();
  static get = (socket: Socket) => {
    return HttpStorageSceneVersionCache.cache.get(socket);
  };
  static set = (
    socket: Socket,
    elements: readonly SyncableExcalidrawElement[],
  ) => {
    HttpStorageSceneVersionCache.cache.set(
      socket,
      hashElementsVersion(elements),
    );
  };
}

export const isSavedToHttpStorage = (
  portal: Portal,
  elements: readonly ExcalidrawElement[],
): boolean => {
  if (portal.socket && portal.roomId && portal.roomKey) {
    const sceneVersion = hashElementsVersion(elements);

    return HttpStorageSceneVersionCache.get(portal.socket) === sceneVersion;
  }
  // if no room exists, consider the room saved so that we don't unnecessarily
  // prevent unload (there's nothing we could do at that point anyway)
  return true;
};

export const saveToHttpStorage: IStorageBackend["saveToStorage"] = async (
  portal: Portal,
  elements: readonly SyncableExcalidrawElement[],
  appState: AppState,
) => {
  const { roomId, roomKey, socket } = portal;
  if (
    !roomId ||
    !roomKey ||
    !socket ||
    isSavedToHttpStorage(portal, elements)
  ) {
    return null;
  }
  const { data: prevStoredScene, status } = await storageApi.get<
    SyncableExcalidrawElement[]
  >(`/rooms/${roomId}`);
  if (!prevStoredScene && status !== 404) {
    return null;
  }

  let storedScene: SyncableExcalidrawElement[] = [...elements];
  if (prevStoredScene) {
    const prevStoredElements = getSyncableElements(prevStoredScene);
    const reconciledElements = getSyncableElements(
      reconcileElements(
        elements,
        prevStoredElements as OrderedExcalidrawElement[] as RemoteExcalidrawElement[],
        appState,
      ),
    );
    storedScene = reconciledElements;
  }
  await storageApi.put(`/rooms/${roomId}`, JSON.stringify(storedScene));

  const storedElements = getSyncableElements(storedScene);

  HttpStorageSceneVersionCache.set(socket, storedElements);

  return storedElements;
};

export const loadFromHttpStorage: IStorageBackend["loadFromStorage"] = async (
  roomId: string,
  roomKey: string,
  socket: Socket | null,
) => {
  const { data: storedElements } = await storageApi.get<
    OrderedExcalidrawElement[]
  >(`/rooms/${roomId}`);

  if (!storedElements) {
    return null;
  }
  const elements = getSyncableElements(storedElements);
  if (socket) {
    HttpStorageSceneVersionCache.set(socket, elements);
  }

  return elements;
};

export const saveFilesToHttpStorage: IStorageBackend["saveFilesToStorage"] =
  async ({ prefix, files }) => {
    const erroredFiles = new Map<FileId, true>();
    const savedFiles = new Map<FileId, true>();

    await Promise.all(
      files.map(async ({ id, buffer }) => {
        try {
          const payloadBlob = new Blob([buffer]);
          const payload = await new Response(payloadBlob).arrayBuffer();
          await fetch(`${HTTP_STORAGE_BACKEND_URL}/files/${id}`, {
            method: "PUT",
            body: payload,
          });
          savedFiles.set(id, true);
        } catch (error: any) {
          erroredFiles.set(id, true);
        }
      }),
    );

    return { savedFiles, erroredFiles };
  };

export const loadFilesFromHttpStorage: IStorageBackend["loadFilesFromStorage"] =
  async (
    prefix: string,
    decryptionKey: string,
    filesIds: readonly FileId[],
  ) => {
    const loadedFiles: BinaryFileData[] = [];
    const erroredFiles = new Map<FileId, true>();

    await Promise.all(
      [...new Set(filesIds)].map(async (id) => {
        try {
          const response = await fetch(
            `${HTTP_STORAGE_BACKEND_URL}/files/${id}`,
          );
          if (response.status < 400) {
            const arrayBuffer = await response.arrayBuffer();

            const { data, metadata } = await decompressData<BinaryFileMetadata>(
              new Uint8Array(arrayBuffer),
              {
                decryptionKey,
              },
            );

            const dataURL = new TextDecoder().decode(data) as DataURL;

            loadedFiles.push({
              mimeType: metadata.mimeType || MIME_TYPES.binary,
              id,
              dataURL,
              created: metadata?.created || Date.now(),
            });
          } else {
            erroredFiles.set(id, true);
          }
        } catch (error: any) {
          erroredFiles.set(id, true);
          console.error(error);
        }
      }),
    );

    return { loadedFiles, erroredFiles };
  };

```

config.ts

```tsx
import {
  isSavedToFirebase,
  loadFilesFromFirebase,
  loadFromFirebase,
  saveFilesToFirebase,
  saveToFirebase,
} from "./firebase";
import {
  isSavedToHttpStorage,
  loadFilesFromHttpStorage,
  loadFromHttpStorage,
  saveFilesToHttpStorage,
  saveToHttpStorage,
} from "./httpStorage";
import type { IStorageBackend } from "./StorageBackend";

const firebaseStorage: IStorageBackend = {
  isSaved: isSavedToFirebase,
  saveToStorage: saveToFirebase,
  loadFromStorage: loadFromFirebase,
  saveFilesToStorage: saveFilesToFirebase,
  loadFilesFromStorage: loadFilesFromFirebase,
};

const httpStorage: IStorageBackend = {
  isSaved: isSavedToHttpStorage,
  saveToStorage: saveToHttpStorage,
  loadFromStorage: loadFromHttpStorage,
  saveFilesToStorage: saveFilesToHttpStorage,
  loadFilesFromStorage: loadFilesFromHttpStorage,
};

const storageBackends = new Map<string, IStorageBackend>([
  ["firebase", firebaseStorage],
  ["http", httpStorage],
]);

async function getStorageBackend() {
  const storageBackendName = import.meta.env.VITE_STORAGE_BACKEND;
  let _storageBackend: IStorageBackend | null = firebaseStorage;

  if (storageBackends.has(storageBackendName)) {
    _storageBackend = storageBackends.get(
      storageBackendName,
    ) as IStorageBackend;
  } else {
    console.warn("No storage backend found, default to firebase");
  }
  return _storageBackend;
}
const storageBackend: IStorageBackend = await getStorageBackend();
export { storageBackend };

```

# Deploying

> Region: `asia-southeast1`
## Google oauth

```json
client_id: <GOOGLE_CLIENT_ID>
client_secret: <GOOGLE_CLIENT_SECRET>
```

## Service Account

```json
{}
```

## Cloud SQL

```json
password: <CLOUD_SQL_PASSWORD>
conenctionName: whiteboard-431816:asia-southeast1:whiteboard
```

## CICD

### Service Account

## Database