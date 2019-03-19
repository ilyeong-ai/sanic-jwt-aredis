## Sanic JWT show-case

The repository is a show-case of basic Sanic functionality using **sanic_jwt**. The show-case implements basic registration, login, logout, refresh token, and current user functionality. Additionally, the repository implements `protected` end-points for a generic _ideas_ database.

The showcase uses HS256 algorithm (for simplicity) and encodes the user name as a `private claim` while email is used as the object identification. 'id' is intentionally not returned, since user-id end-points have not been implemented.


The show-case uses REDIS as a key-value store for refresh-tokens. The implementation uses **aredis**, however could **aioredis** could have been used instead. 

User information is stored in a **SQLite3** database, with a basic user schema. Users email, functions as the _unique id_ for a user. However, note that users are filtered with an expiration timestamp, allowing for future re-use of emails. 

the Idea schema show-cases modifications timestamps.

The JWT implementation slightly deviates from the boiler plate implementation:

* `/me` end-point returns the user details in a JSON w/o wrapping with a 'me' key. 
* *authentication* uses an X- header which are becoming less fashionable. It is possible to modift the implementation to switch the X- header to an `Authorization` header, with a `Bear` for the JWT token.
      

