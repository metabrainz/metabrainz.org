type Scope = {
  name: string;
  description: string;
};

type Application = {
  name: string;
  description: string;
  website: string;
};

type SupporterState = "active" | "rejected" | "pending" | "waiting" | "limited";

type Tier = {
  name: string;
};

type Dataset = {
  id: number;
  name: string;
  description: string;
};

type Supporter = {
  datasets: Array<Dataset>;
  is_commercial: boolean;
  tier: Tier;
  state: SupporterState;
  contact_name: string;
  org_name?: string;
  api_url?: string;
  website_url?: string;
  good_standing: boolean;
  token?: string;
};

type User = {
  name: string;
  email: string;
  is_email_confirmed: boolean;
  supporter?: Supporter;
};
