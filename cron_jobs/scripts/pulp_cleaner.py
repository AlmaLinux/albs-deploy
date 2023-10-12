import asyncio
import logging
import os
import pprint
from datetime import datetime
from typing import Optional

import aiohttp


class PulpCleaner:
    def __init__(
        self,
        pulp_login: str,
        pulp_password: str,
        pulp_host: str,
        concurrency_limit: str,
    ):
        if not pulp_login or not pulp_password:
            raise ValueError('"pulp_login" or "pulp_password" are empty')
        self.semaphore = asyncio.Semaphore(int(concurrency_limit))
        self.pulp_host = pulp_host
        self.auth = aiohttp.BasicAuth(pulp_login, pulp_password)
        self.logger = self.configure_logger()

    def configure_logger(self) -> logging.Logger:
        logger = logging.getLogger('pulp-cleaner')
        logger.setLevel(logging.INFO)
        logger.addHandler(logging.StreamHandler())
        return logger

    def prepare_endpoint(self, endpoint: str) -> str:
        return f'{self.pulp_host}{endpoint}'

    async def make_request(
        self,
        url: str,
        method: str = 'GET',
        json: Optional[dict] = None,
    ):
        async with aiohttp.request(
            method=method,
            url=url,
            auth=self.auth,
            json=json,
        ) as response:
            return await response.json()

    async def wait_for_task(self, task_href: str):
        endpoint = self.prepare_endpoint(task_href)
        task = await self.make_request(endpoint)
        while task['state'] not in ('failed', 'completed'):
            await asyncio.sleep(5)
            task = await self.make_request(endpoint)
        if task['state'] == 'failed':
            raise ValueError(
                f'Task {task_href} failed. '
                f'Task details:\n{pprint.pformat(task)}'
            )
        return task

    async def get_all_exporters(self):
        self.logger.info('Retrieving existing exporters...')
        return await self.make_request(
            self.prepare_endpoint(
                '/pulp/api/v3/exporters/core/filesystem/?limit=1000&fields=pulp_href'
            ),
        )

    async def delete_exporter(self, exporter_href: str):
        async with self.semaphore:
            self.logger.info('Removing "%s" exporter...', exporter_href)
            response = await self.make_request(
                self.prepare_endpoint(exporter_href),
                method='DELETE',
            )
            await self.wait_for_task(response['task'])
            self.logger.info('Exporter "%s" removed', exporter_href)

    async def purge_old_tasks(self):
        today = datetime.today().strftime('%Y-%m-%dT00:00')
        self.logger.info('Removing completed pulp tasks before "%s"...', today)
        response = await self.make_request(
            self.prepare_endpoint('/pulp/api/v3/tasks/purge/'),
            method='POST',
            json={'finished_before': today},
        )
        await self.wait_for_task(response['task'])
        self.logger.info('Completed pulp tasks were removed')

    async def run(self):
        exporters = await self.get_all_exporters()
        await asyncio.gather(
            *(
                self.delete_exporter(exporter['pulp_href'])
                for exporter in exporters.get('results', [])
            )
        )
        await self.purge_old_tasks()


async def main():
    pulp_cleaner = PulpCleaner(
        pulp_login=os.getenv('PULP_USERNAME', 'admin'),
        pulp_password=os.getenv('PULP_PASSWORD', ''),
        pulp_host=os.getenv('PULP_HOST', 'http://pulp'),
        concurrency_limit=os.getenv('CLEANER_CONCURRENCY_LIMIT', '10'),
    )
    await pulp_cleaner.run()


if __name__ == '__main__':
    asyncio.run(main())
