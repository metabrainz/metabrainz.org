import React from "react";
import { ProjectIconPills } from "./utils";

export default function ConditionsModal() {
  return (
    <div className="modal fade" id="conditions-modal">
      <div className="modal-dialog" role="document">
        <div className="modal-content">
          <div className="modal-header">
            <button
              type="button"
              className="close"
              data-dismiss="modal"
              aria-label="Close"
            >
              <span aria-hidden="true">&times;</span>
            </button>
            <h4 className="modal-title">Privacy policy</h4>
          </div>
          <h5>Licensing</h5>
          <p>
            Any contributions you make to MusicBrainz will be released into the
            Public Domain and/or licensed under a Creative Commons by-nc-sa
            license. Furthermore, you give the MetaBrainz Foundation the right
            to license this data for commercial use.
            <br />
            Please read our{" "}
            <a
              target="_blank"
              rel="noopener noreferrer"
              href="/social-contract"
            >
              {" "}
              license page
            </a>{" "}
            for more details.
          </p>
          <h5>Privacy</h5>
          <p>
            MusicBrainz strongly believes in the privacy of its users. Any
            personal information you choose to provide will not be sold or
            shared with anyone else.
            <br />
            Please read our{" "}
            <a target="_blank" rel="noopener noreferrer" href="/privacy">
              privacy policy
            </a>{" "}
            for more details.
          </p>
          <h5>GDPR compliance</h5>
          <p>
            You may remove your personal information from our services anytime
            by deleting your account.
            <br />
            Please read our{" "}
            <a target="_blank" rel="noopener noreferrer" href="/gdpr">
              GDPR compliance statement
            </a>{" "}
            for more details.
          </p>
          <hr />
          <ProjectIconPills />
          <p>
            Creating an account on MetaBrainz will give you access to all of our
            projects, such as MusicBrainz, ListenBrainz, BookBrainz, and more.
            <br />
            We do not automatically create accounts for these services when you
            create a MetaBrainz account, but you will be just a few clicks away
            from doing so.
          </p>
          <button
            className="btn btn-primary center-block"
            type="button"
            data-dismiss="modal"
          >
            Sounds good
          </button>
        </div>
      </div>
    </div>
  );
}
