<script>
	import '@evidence-dev/tailwind/fonts.css';
	import '../app.css';
	import { EvidenceDefaultLayout } from '@evidence-dev/core-components';
	export let data;
</script>

<!--
  Layout overrides: show the project name instead of the framework wordmark,
  drop the "Built with Evidence" footer, hide the dev-mode query inspectors,
  and put the repo link in the header.
-->
<EvidenceDefaultLayout
	{data}
	title="Energy Grid Dashboard"
	builtWithEvidence={false}
	neverShowQueries={true}
	githubRepo="https://github.com/bolat-t/Energy-Grid-Dashboard"
>
	<slot slot="content" />
</EvidenceDefaultLayout>
